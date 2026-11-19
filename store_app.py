import io
import os
import re
import random
import hashlib
import warnings
import itertools
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import CosineAnnealingLR
import xgboost as xgb
import easyocr

warnings.filterwarnings("ignore")

# ==========================================
# PAGE CONFIGURATION & ARTIFACT STORAGE
# ==========================================
st.set_page_config(
    page_title="Retail AI Replenishment & Sales Portal",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

MODEL_DIR = "saved_artifacts"
os.makedirs(MODEL_DIR, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# ==========================================
# AUTHENTICATION MODULE (STORE OWNER LOGIN)
# ==========================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

USERS_DB = {
    "owner": {
        "name": "Store Owner (Guru Liquor)",
        "password_hash": hash_password("KansasCity2026!"),
        "role": "admin"
    },
    "rashad": {
        "name": "Rashad Jafarov (Analytics Lead)",
        "password_hash": hash_password("SEASUG2026!"),
        "role": "admin"
    }
}

def check_authentication():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None

    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown("## 🔐 Store Replenishment Portal")
            st.caption("SEASUG 2026 Automated Inventory & Demand Forecasting System")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username (e.g., owner)")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

                if submitted:
                    user = USERS_DB.get(username.strip().lower())
                    if user and user["password_hash"] == hash_password(password):
                        st.session_state.authenticated = True
                        st.session_state.user_info = user
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
        st.stop()

check_authentication()

# ==========================================
# ML ARCHITECTURE DEFINITIONS (STAGE 1)
# ==========================================
class DynamicLSTMModel(nn.Module):
    def __init__(self, input_dim, hidden_dim=32, num_layers=1, dropout=0.15):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc1 = nn.Linear(hidden_dim, 20)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(20, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc1(out[:, -1, :])
        out = self.relu(out)
        out = self.dropout(out)
        return self.fc2(out)

def create_weekly_sequences(X_data, y_data, seq_length=4):
    X_seq, y_seq = [], []
    for i in range(len(X_data) - seq_length + 1):
        X_seq.append(X_data[i:i + seq_length])
        y_seq.append(y_data[i + seq_length - 1])
    return np.array(X_seq), np.array(y_seq)

def compute_wape(y_true, y_pred):
    return (np.sum(np.abs(y_true - y_pred)) / (np.sum(y_true) + 1e-8)) * 100

def compute_metrics_full(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if np.sum(mask) > 0 else 0.0
    wape = compute_wape(y_true, y_pred)
    return round(rmse, 4), round(r2, 4), round(mape, 2), round(wape, 2)

def compute_features(df_input):
    df = df_input.copy().sort_values(by=['SKU', 'Clean_Date']).reset_index(drop=True)
    df['Lag_1'] = df.groupby('SKU')['Sales'].shift(1)
    df['Lag_2'] = df.groupby('SKU')['Sales'].shift(2)
    df['Lag_4'] = df.groupby('SKU')['Sales'].shift(4)
    df['Rolling_Mean_4'] = df.groupby('SKU')['Sales'].transform(lambda x: x.shift(1).rolling(4).mean())
    df['Month'] = df['Clean_Date'].dt.month
    df['SKU_Code'] = df['SKU'].astype('category').cat.codes
    return df.dropna().reset_index(drop=True)

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

# ==========================================
# STAGE 1 BACKEND PIPELINE
# ==========================================
def run_stage_1_training(df_raw, progress_bar, status_text):
    status_text.text("Step 1/5: Preparing dual-format panel datasets...")
    progress_bar.progress(10)

    df_raw_c1 = df_raw.copy()
    if 'Weeks' in df_raw_c1.columns:
        df_raw_c1['Date'] = pd.to_datetime(
            df_raw_c1['Weeks'].str.split('-').str[1], format='%m/%d/%y'
        )
        non_sku_cols_c1 = ['No', 'Weeks', 'Total Weekly Volume', 'Date']
        sku_cols_c1 = [col for col in df_raw_c1.columns if col not in non_sku_cols_c1]
        df_c1 = df_raw_c1.melt(
            id_vars=['Date', 'Weeks'],
            value_vars=sku_cols_c1,
            var_name='Product Name',
            value_name='Quantity Sold (units)',
        )
    else:
        df_c1 = df_raw_c1.copy()
        date_col_src = 'Transaction Time' if 'Transaction Time' in df_c1.columns else 'Date'
        df_c1['Date'] = pd.to_datetime(df_c1[date_col_src])

    target_col = 'Quantity Sold (units)'
    sku_col = 'Product Name'
    date_col = 'Date'

    df_c1[target_col] = pd.to_numeric(
        df_c1[target_col].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
        errors='coerce',
    ).fillna(0)
    df_c1 = df_c1.dropna(subset=[date_col, sku_col, target_col])

    sku_counts = df_c1.groupby(sku_col)[target_col].count()
    valid_skus = sku_counts[sku_counts >= 10].index.tolist()

    # Format 2: XGBoost & LSTM Panel
    df_raw_c2 = df_raw.copy()
    if 'Weeks' in df_raw_c2.columns:
        df_raw_c2['Clean_Date'] = pd.to_datetime(
            df_raw_c2['Weeks'].astype(str).str.split('-').str[0].str.strip(), errors='coerce'
        )
        non_sku_cols_c2 = {'No', 'Weeks', 'Clean_Date', 'Total Weekly Volume'}
        sku_cols_c2 = [col for col in df_raw_c2.columns if col not in non_sku_cols_c2]
        df_melted_c2 = df_raw_c2.melt(
            id_vars=['Clean_Date'], value_vars=sku_cols_c2, var_name='SKU', value_name='Sales'
        )
    else:
        df_melted_c2 = df_c1.rename(columns={date_col: 'Clean_Date', sku_col: 'SKU', target_col: 'Sales'}).copy()

    df_melted_c2['Sales'] = pd.to_numeric(
        df_melted_c2['Sales'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
        errors='coerce'
    ).fillna(0)

    df_panel = df_melted_c2.dropna(subset=['Clean_Date', 'SKU']).sort_values(by=['SKU', 'Clean_Date']).reset_index(drop=True)
    df_panel = df_panel[df_panel['SKU'].isin(valid_skus)].reset_index(drop=True)

    # ADF Stationarity Check
    total_sales_series = df_c1.groupby(date_col)[target_col].sum().dropna()
    adf_res = adfuller(total_sales_series)

    # 6-Fold Fixed-Horizon CV Setup
    unique_dates_c2 = sorted(df_panel['Clean_Date'].unique())
    total_weeks = len(unique_dates_c2)
    val_len = 8
    num_folds = 6

    fold_splits = []
    for i in range(num_folds):
        val_end_idx = total_weeks - 1 - (num_folds - 1 - i) * val_len
        val_start_idx = val_end_idx - val_len + 1
        tr_dates = unique_dates_c2[:val_start_idx]
        va_dates = unique_dates_c2[val_start_idx:val_end_idx + 1]
        fold_splits.append((tr_dates, va_dates))

    train_dates_c2 = fold_splits[-1][0]
    test_date_c2 = fold_splits[-1][1]

    train_df_raw = df_panel[df_panel['Clean_Date'].isin(train_dates_c2)].reset_index(drop=True)
    train_df = compute_features(train_df_raw)
    df_full_fe = compute_features(df_panel)
    test_df = df_full_fe[df_full_fe['Clean_Date'].isin(test_date_c2)].reset_index(drop=True)

    features = ['Lag_1', 'Lag_2', 'Lag_4', 'Rolling_Mean_4', 'Month', 'SKU_Code']
    X_tr_global, y_tr_global = train_df[features], train_df['Sales']
    X_te_global, y_te_global = test_df[features], test_df['Sales']

    # Step 2: Tune XGBoost
    status_text.text("Step 2/5: Tuning Global XGBoost across 6-Fold Cross-Validation...")
    progress_bar.progress(35)

    best_xgb_score = float('-inf')
    best_xgb_params = None

    xgb_param_grid = {
        'n_estimators': [150, 300],
        'learning_rate': [0.03, 0.05],
        'max_depth': [3, 4],
        'subsample': [0.8, 0.9]
    }

    for combo in itertools.product(*xgb_param_grid.values()):
        params = dict(zip(xgb_param_grid.keys(), combo))
        model = xgb.XGBRegressor(**params, objective='reg:squarederror', random_state=42, n_jobs=-1)
        fold_r2s = []
        for tr_d, va_d in fold_splits:
            tr_sub = train_df[train_df['Clean_Date'].isin(tr_d)]
            va_sub = train_df[train_df['Clean_Date'].isin(va_d)]
            if len(tr_sub) == 0 or len(va_sub) == 0:
                continue
            model.fit(tr_sub[features], tr_sub['Sales'])
            preds = np.maximum(0, model.predict(va_sub[features]))
            fold_r2s.append(r2_score(va_sub['Sales'], preds))
        mean_r2 = np.mean(fold_r2s) if fold_r2s else -999
        if mean_r2 > best_xgb_score:
            best_xgb_score = mean_r2
            best_xgb_params = params

    best_xgb = xgb.XGBRegressor(**best_xgb_params, objective='reg:squarederror', random_state=42, n_jobs=-1)
    best_xgb.fit(X_tr_global, y_tr_global)
    train_df['XGB_Pred'] = np.maximum(0, best_xgb.predict(X_tr_global))
    test_df['XGB_Pred'] = np.maximum(0, best_xgb.predict(X_te_global))

    # Step 3: Tune LSTM
    status_text.text("Step 3/5: Tuning PyTorch LSTM Architecture across 6-Fold CV...")
    progress_bar.progress(65)

    lstm_grid = [
        {'hidden_dim': 24, 'lr': 0.003, 'seq_length': 4},
        {'hidden_dim': 32, 'lr': 0.005, 'seq_length': 4}
    ]

    best_score = float('inf')
    best_lstm_params = lstm_grid[0]

    for config in lstm_grid:
        fold_mses = []
        for tr_d, va_d in fold_splits:
            sub_tr = train_df[train_df['Clean_Date'].isin(tr_d)]
            sub_va = train_df[train_df['Clean_Date'].isin(va_d)]
            fold_sku_preds, fold_sku_trues = [], []
            for sku in valid_skus:
                s_tr, s_va = sub_tr[sub_tr['SKU'] == sku], sub_va[sub_va['SKU'] == sku]
                if len(s_tr) < 8 or len(s_va) == 0:
                    continue
                scaler_X, scaler_y = StandardScaler(), StandardScaler()
                X_tr = scaler_X.fit_transform(s_tr[features])
                y_tr = scaler_y.fit_transform(s_tr['Sales'].values.reshape(-1, 1)).flatten()
                full_sub = pd.concat([s_tr.tail(config['seq_length'] - 1), s_va])
                X_va_full = scaler_X.transform(full_sub[features])
                y_va = s_va['Sales'].values

                X_seq_tr, y_seq_tr = create_weekly_sequences(X_tr, y_tr, seq_length=config['seq_length'])
                X_seq_va, _ = create_weekly_sequences(X_va_full, np.zeros(len(X_va_full)), seq_length=config['seq_length'])
                if len(X_seq_tr) == 0 or len(X_seq_va) == 0:
                    continue

                net = DynamicLSTMModel(input_dim=len(features), hidden_dim=config['hidden_dim'])
                opt = torch.optim.AdamW(net.parameters(), lr=config['lr'], weight_decay=5e-4)
                crit = nn.HuberLoss()
                X_tr_t = torch.tensor(X_seq_tr, dtype=torch.float32)
                y_tr_t = torch.tensor(y_seq_tr, dtype=torch.float32).unsqueeze(1)
                X_va_t = torch.tensor(X_seq_va, dtype=torch.float32)

                net.train()
                for _ in range(25):
                    opt.zero_grad()
                    loss = crit(net(X_tr_t), y_tr_t)
                    loss.backward()
                    opt.step()

                net.eval()
                with torch.no_grad():
                    preds = scaler_y.inverse_transform(net(X_va_t).numpy()).flatten()
                fold_sku_preds.extend(np.maximum(0, preds[-len(y_va):]))
                fold_sku_trues.extend(y_va)

            if fold_sku_trues:
                fold_mses.append(mean_squared_error(fold_sku_trues, fold_sku_preds))

        if fold_mses and np.mean(fold_mses) < best_score:
            best_score = np.mean(fold_mses)
            best_lstm_params = config

    # Step 4: Train final per-SKU LSTM models & save artifacts
    status_text.text("Step 4/5: Training final SKU-level LSTM models & calculating Inverse-WAPE weights...")
    progress_bar.progress(85)

    train_df['LSTM_Pred'] = 0.0
    test_df['LSTM_Pred'] = 0.0
    saved_lstm_bundles = {}

    for sku in valid_skus:
        tr_mask = train_df['SKU'] == sku
        te_mask = test_df['SKU'] == sku
        sku_tr, sku_te = train_df[tr_mask], test_df[te_mask]
        mean_val = sku_tr['Sales'].mean() if len(sku_tr) > 0 else 0.0

        if len(sku_tr) < 8 or len(sku_te) == 0:
            train_df.loc[tr_mask, 'LSTM_Pred'] = mean_val
            test_df.loc[te_mask, 'LSTM_Pred'] = mean_val
            continue

        scaler_X, scaler_y = StandardScaler(), StandardScaler()
        X_tr_sc = scaler_X.fit_transform(sku_tr[features])
        y_tr_sc = scaler_y.fit_transform(sku_tr['Sales'].values.reshape(-1, 1)).flatten()

        seq_len = best_lstm_params['seq_length']
        sku_full_buffer = pd.concat([sku_tr.tail(seq_len - 1), sku_te])
        X_full_sc = scaler_X.transform(sku_full_buffer[features])

        X_seq_tr, y_seq_tr = create_weekly_sequences(X_tr_sc, y_tr_sc, seq_length=seq_len)
        X_seq_full, _ = create_weekly_sequences(X_full_sc, np.zeros(len(X_full_sc)), seq_length=seq_len)
        X_seq_te = X_seq_full[-len(sku_te):]

        if len(X_seq_tr) > 0 and len(X_seq_te) > 0:
            torch.manual_seed(42)
            lstm_net = DynamicLSTMModel(input_dim=len(features), hidden_dim=best_lstm_params['hidden_dim'])
            optimizer = torch.optim.AdamW(lstm_net.parameters(), lr=best_lstm_params['lr'], weight_decay=5e-4)
            scheduler = CosineAnnealingLR(optimizer, T_max=80, eta_min=1e-5)
            criterion = nn.HuberLoss()

            X_seq_tr_t = torch.tensor(X_seq_tr, dtype=torch.float32)
            y_seq_tr_t = torch.tensor(y_seq_tr, dtype=torch.float32).unsqueeze(1)
            X_seq_te_t = torch.tensor(X_seq_te, dtype=torch.float32)

            lstm_net.train()
            for _ in range(80):
                optimizer.zero_grad()
                loss = criterion(lstm_net(X_seq_tr_t), y_seq_tr_t)
                loss.backward()
                optimizer.step()
                scheduler.step()

            lstm_net.eval()
            with torch.no_grad():
                lstm_tr_unscaled = scaler_y.inverse_transform(lstm_net(X_seq_tr_t).numpy()).flatten()
                lstm_te_unscaled = scaler_y.inverse_transform(lstm_net(X_seq_te_t).numpy()).flatten()

            pad_len = len(sku_tr) - len(lstm_tr_unscaled)
            lstm_tr_final = np.concatenate([sku_tr['Sales'].values[:pad_len], lstm_tr_unscaled])
            train_df.loc[tr_mask, 'LSTM_Pred'] = np.maximum(0, lstm_tr_final)
            test_df.loc[te_mask, 'LSTM_Pred'] = np.maximum(0, lstm_te_unscaled)

            saved_lstm_bundles[sku] = {
                "state_dict": lstm_net.state_dict(),
                "scaler_X": scaler_X,
                "scaler_y": scaler_y,
                "hidden_dim": best_lstm_params['hidden_dim'],
                "seq_length": seq_len
            }

    # Dynamic Inverse-WAPE Ensemble
    wape_xgb = compute_wape(train_df['Sales'].values, train_df['XGB_Pred'].values)
    wape_lstm = compute_wape(train_df['Sales'].values, train_df['LSTM_Pred'].values)
    inv_wapes = np.array([1.0 / (wape_xgb + 1e-6), 1.0 / (wape_lstm + 1e-6)])
    weights = inv_wapes / np.sum(inv_wapes)

    train_df['Ensemble_Pred'] = weights[0] * train_df['XGB_Pred'] + weights[1] * train_df['LSTM_Pred']
    test_df['Ensemble_Pred'] = weights[0] * test_df['XGB_Pred'] + weights[1] * test_df['LSTM_Pred']

    # Build Diagnostic Summary Table
    xgb_tr_m = compute_metrics_full(train_df['Sales'].values, train_df['XGB_Pred'].values)
    xgb_te_m = compute_metrics_full(test_df['Sales'].values, test_df['XGB_Pred'].values)
    lstm_tr_m = compute_metrics_full(train_df['Sales'].values, train_df['LSTM_Pred'].values)
    lstm_te_m = compute_metrics_full(test_df['Sales'].values, test_df['LSTM_Pred'].values)
    ens_tr_m = compute_metrics_full(train_df['Sales'].values, train_df['Ensemble_Pred'].values)
    ens_te_m = compute_metrics_full(test_df['Sales'].values, test_df['Ensemble_Pred'].values)

    diag_df = pd.DataFrame([
        {'Model': 'XGBoost (Global CV Tuned)', 'Train RMSE': xgb_tr_m[0], 'Test RMSE': xgb_te_m[0], 'Train R²': xgb_tr_m[1], 'Test R²': xgb_te_m[1], 'Test WAPE (%)': xgb_te_m[3]},
        {'Model': 'LSTM (CV Architecture Tuned)', 'Train RMSE': lstm_tr_m[0], 'Test RMSE': lstm_te_m[0], 'Train R²': lstm_tr_m[1], 'Test R²': lstm_te_m[1], 'Test WAPE (%)': lstm_te_m[3]},
        {'Model': 'Dynamic Inverse-WAPE Ensemble (XGB+LSTM)', 'Train RMSE': ens_tr_m[0], 'Test RMSE': ens_te_m[0], 'Train R²': ens_tr_m[1], 'Test R²': ens_te_m[1], 'Test WAPE (%)': ens_te_m[3]},
    ])

    top_skus_sorted = (
        df_c1[df_c1[sku_col].isin(valid_skus)]
        .groupby(sku_col)[target_col]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    status_text.text("Step 5/5: Saving tuned models and historical artifacts for Stage 2...")
    joblib.dump(df_c1, os.path.join(MODEL_DIR, 'historical_sales.pkl'))
    joblib.dump(df_panel, os.path.join(MODEL_DIR, 'df_panel.pkl'))
    joblib.dump(top_skus_sorted, os.path.join(MODEL_DIR, 'top_skus.pkl'))
    joblib.dump(best_xgb, os.path.join(MODEL_DIR, 'best_xgb.pkl'))
    joblib.dump(saved_lstm_bundles, os.path.join(MODEL_DIR, 'lstm_bundles.pkl'))
    joblib.dump({
        "weights": weights,
        "best_xgb_params": best_xgb_params,
        "best_lstm_params": best_lstm_params,
        "diag_df": diag_df,
        "adf_stat": adf_res[0],
        "adf_p": adf_res[1],
        "total_sales_series": total_sales_series,
        "test_df": test_df
    }, os.path.join(MODEL_DIR, 'model_metadata.pkl'))

    progress_bar.progress(100)
    status_text.text("✅ Stage 1 Training Complete! Tuned models saved for weekly ordering.")

# ==========================================
# STAGE 2 BACKEND PIPELINE (TRUE MODEL INFERENCE)
# ==========================================
def run_stage_2_replenishment(stock_bytes, stock_name, sales_bytes, ocr_bytes, ocr_name, buffer_units, sleeve_size):
    df_panel = joblib.load(os.path.join(MODEL_DIR, 'df_panel.pkl'))
    raw_skus = joblib.load(os.path.join(MODEL_DIR, 'top_skus.pkl'))
    best_xgb = joblib.load(os.path.join(MODEL_DIR, 'best_xgb.pkl'))
    lstm_bundles = joblib.load(os.path.join(MODEL_DIR, 'lstm_bundles.pkl'))
    meta = joblib.load(os.path.join(MODEL_DIR, 'model_metadata.pkl'))

    w_xgb, w_lstm = meta["weights"][0], meta["weights"][1]

    exclude_items = {'nof merchandise', 'blk tip smooth', 'cigarettes', 'dutch gold fusion'}
    selected_skus = [sku for sku in raw_skus if sku.strip().lower() not in exclude_items]

    # 1. Parse Starting Stock
    stock_df = pd.read_excel(io.BytesIO(stock_bytes)) if stock_name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(stock_bytes))
    stock_sku_col = [c for c in stock_df.columns if any(k in c.lower() for k in ['sku', 'product', 'item', 'name'])][0]
    stock_qty_col = [c for c in stock_df.columns if any(k in c.lower() for k in ['inv', 'stock', 'qty', 'quantity', 'col 1'])][0]
    start_inventory_dict = dict(zip(stock_df[stock_sku_col].astype(str).str.strip(), pd.to_numeric(stock_df[stock_qty_col], errors='coerce').fillna(0)))

    # 2. Parse Past 7-Day Sales
    new_sales_df = pd.read_excel(io.BytesIO(sales_bytes))
    sku_col = 'Product Name'
    target_col = 'Quantity Sold (units)'

    # 3. Parse Delivery Invoice (EasyOCR or Excel/CSV)
    ocr_delivery_dict = {sku: 0.0 for sku in selected_skus}
    if ocr_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        reader = load_ocr_reader()
        ocr_results = reader.readtext(ocr_bytes, detail=0)
        for i, text in enumerate(ocr_results):
            for sku in selected_skus:
                sku_words = [w.lower() for w in sku.split() if len(w) > 2][:2]
                if sku_words and all(w in text.lower() for w in sku_words):
                    for offset in range(0, 5):
                        if i + offset < len(ocr_results):
                            nums = re.findall(r'\b\d+\b', ocr_results[i + offset])
                            valid_nums = [float(n) for n in nums if float(n) <= 50]
                            if valid_nums:
                                ocr_delivery_dict[sku] = valid_nums[-1]
                                break
    else:
        ocr_df = pd.read_excel(io.BytesIO(ocr_bytes)) if ocr_name.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(ocr_bytes))
        if not ocr_df.empty:
            p_col = [c for c in ocr_df.columns if any(k in c.lower() for k in ['product', 'sku', 'item', 'description', 'name'])][0]
            q_col = [c for c in ocr_df.columns if any(k in c.lower() for k in ['delivered', 'delivery', 'qty', 'quantity', 'col 2', 'units'])][0]
            ocr_df[q_col] = pd.to_numeric(ocr_df[q_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            extracted_dict = dict(zip(ocr_df[p_col].astype(str).str.strip(), ocr_df[q_col]))
            for target_sku in selected_skus:
                for extracted_key, qty in extracted_dict.items():
                    if target_sku.lower().strip() in extracted_key.lower().strip() or extracted_key.lower().strip() in target_sku.lower().strip():
                        ocr_delivery_dict[target_sku] = float(qty)
                        break

    next_week_date = df_panel['Clean_Date'].max() + pd.Timedelta(days=7)
    new_week_rows = []
    for sku in selected_skus:
        past_7d_sales = float(new_sales_df[new_sales_df[sku_col] == sku][target_col].sum()) if sku in new_sales_df[sku_col].values else 0.0
        new_week_rows.append({'Clean_Date': next_week_date, 'SKU': sku, 'Sales': past_7d_sales})

    forecast_target_date = next_week_date + pd.Timedelta(days=7)
    future_dummy_rows = [{'Clean_Date': forecast_target_date, 'SKU': sku, 'Sales': 0.0} for sku in selected_skus]

    extended_panel = pd.concat([df_panel, pd.DataFrame(new_week_rows), pd.DataFrame(future_dummy_rows)], ignore_index=True)
    extended_fe = compute_features(extended_panel)
    next_week_features = extended_fe[extended_fe['Clean_Date'] == forecast_target_date].copy()

    features = ['Lag_1', 'Lag_2', 'Lag_4', 'Rolling_Mean_4', 'Month', 'SKU_Code']
    if not next_week_features.empty:
        next_week_features['XGB_Next'] = np.maximum(0, best_xgb.predict(next_week_features[features]))
    xgb_next_map = dict(zip(next_week_features['SKU'], next_week_features['XGB_Next'])) if not next_week_features.empty else {}

    top_10_skus = selected_skus[:10]
    master_rows = []

    for sku in selected_skus:
        inv_start = float(start_inventory_dict.get(sku, 0.0))
        delivered = float(ocr_delivery_dict.get(sku, 0.0))
        past_7d_sales = float(new_sales_df[new_sales_df[sku_col] == sku][target_col].sum()) if sku in new_sales_df[sku_col].values else 0.0
        sunday_inv = inv_start + delivered - past_7d_sales

        p_xgb = float(xgb_next_map.get(sku, past_7d_sales))
        p_lstm = past_7d_sales
        if sku in lstm_bundles:
            bundle = lstm_bundles[sku]
            sku_hist_fe = extended_fe[extended_fe['SKU'] == sku].sort_values('Clean_Date').tail(bundle['seq_length'])
            if len(sku_hist_fe) == bundle['seq_length']:
                X_sc = bundle['scaler_X'].transform(sku_hist_fe[features])
                X_t = torch.tensor(X_sc[np.newaxis, :, :], dtype=torch.float32)
                net = DynamicLSTMModel(input_dim=len(features), hidden_dim=bundle['hidden_dim'])
                net.load_state_dict(bundle['state_dict'])
                net.eval()
                with torch.no_grad():
                    pred_sc = net(X_t).numpy()
                p_lstm = float(np.maximum(0, bundle['scaler_y'].inverse_transform(pred_sc).flatten()[0]))

        ensemble_pred = (w_xgb * p_xgb) + (w_lstm * p_lstm)
        deficit = ensemble_pred - sunday_inv
        if sku in top_10_skus:
            deficit += buffer_units

        reorder_sleeves = int(np.ceil(max(0, deficit) / float(sleeve_size)))

        master_rows.append({
            'SKU': sku,
            'Stock Inventory': int(round(inv_start)),
            'New Delivery': int(round(delivered)),
            'Past 7D Sales': int(round(past_7d_sales)),
            'Sunday Inv': int(round(sunday_inv)),
            'XGB Forecast': int(round(p_xgb)),
            'LSTM Forecast': int(round(p_lstm)),
            'Ensemble Forecast': int(round(ensemble_pred)),
            'Net Deficit': int(round(deficit)),
            'Order Next Week (Sleeves)': int(reorder_sleeves),
            'Order Total Units': int(reorder_sleeves * sleeve_size)
        })

    return pd.DataFrame(master_rows)

# ==========================================
# SIDEBAR NAVIGATION & USER STATUS
# ==========================================
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_info['name']}")
    st.caption("Status: Authenticated Session")
    if st.button("Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

    st.divider()
    page = st.radio(
        "Navigation",
        [
            "🛒 Weekly Replenishment & Orders (Stage 2)",
            "🧠 Model Training & 6-Fold CV (Stage 1)",
            "📊 Model Performance & Diagnostics"
        ]
    )

    st.divider()
    model_ready = os.path.exists(os.path.join(MODEL_DIR, 'model_metadata.pkl'))
    if model_ready:
        st.success("✅ Tuned Ensemble Models Loaded")
    else:
        st.warning("⚠️ No trained model found. Run Stage 1 first.")

# ==========================================
# PAGE 1: STAGE 2 SUNDAY REPLENISHMENT GUI
# ==========================================
if page == "🛒 Weekly Replenishment & Orders (Stage 2)":
    st.title("🛒 Next-Week Inventory Forecast & Wholesale Order Generator")
    st.markdown("Upload your current stock sheet, past 7-day POS sales, and distributor delivery invoice (image or spreadsheet) to compute next week's optimal SKU order.")

    if not model_ready:
        st.error("Please go to **Model Training & 6-Fold CV (Stage 1)** in the sidebar and upload your historical dataset first.")
        st.stop()

    with st.expander("⚙️ Ordering Parameters (Buffer & Sleeve Batching)", expanded=False):
        c1, c2 = st.columns(2)
        buffer_units = c1.number_input("Safety Buffer Stock for Top-10 SKUs (Units)", min_value=0, max_value=50, value=5)
        sleeve_size = c2.number_input("Wholesale Batch / Sleeve Size (Units)", min_value=1, max_value=50, value=10)

    col_up1, col_up2, col_up3 = st.columns(3)
    with col_up1:
        stock_file = st.file_uploader("1. Initial Stock Inventory (CSV / XLSX)", type=["csv", "xlsx", "xls"])
    with col_up2:
        sales_file = st.file_uploader("2. Past 7-Day POS Sales (XLSX)", type=["xlsx", "xls"])
    with col_up3:
        invoice_file = st.file_uploader("3. Delivery Invoice (JPG, PNG, CSV, XLSX)", type=["jpg", "jpeg", "png", "csv", "xlsx", "xls"])

    if st.button("🚀 Generate Next-Week Forecast & Order List", type="primary", use_container_width=True):
        if not (stock_file and sales_file and invoice_file):
            st.warning("Please upload all three required files before running the forecast.")
        else:
            with st.spinner("Running EasyOCR invoice parsing and Dynamic Inverse-WAPE Ensemble inference..."):
                master_table = run_stage_2_replenishment(
                    stock_file.read(), stock_file.name,
                    sales_file.read(),
                    invoice_file.read(), invoice_file.name,
                    buffer_units, sleeve_size
                )
                st.session_state["latest_master_table"] = master_table

    if "latest_master_table" in st.session_state:
        master_table = st.session_state["latest_master_table"]
        order_list_df = master_table[master_table['Order Next Week (Sleeves)'] > 0][
            ['SKU', 'Sunday Inv', 'Ensemble Forecast', 'Net Deficit', 'Order Next Week (Sleeves)', 'Order Total Units']
        ]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("SKUs Evaluated", len(master_table))
        k2.metric("SKUs Needing Reorder", len(order_list_df))
        k3.metric("Total Sleeves to Order", int(order_list_df['Order Next Week (Sleeves)'].sum()))
        k4.metric("Total Predicted Next-Week Demand", f"{int(master_table['Ensemble Forecast'].sum())} units")

        st.subheader("📋 Final Wholesale Order List (Quantities > 0)")
        st.dataframe(order_list_df, use_container_width=True, hide_index=True)

        csv_orders = order_list_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Final Wholesale Order List (CSV)",
            data=csv_orders,
            file_name=f"wholesale_order_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )

        st.subheader("📊 Interactive Inventory vs. Forecast Comparison")
        fig = go.Figure(data=[
            go.Bar(name='Sunday On-Hand Inv', x=master_table['SKU'], y=master_table['Sunday Inv'], marker_color='#4C78A8'),
            go.Bar(name='Next-Week Ensemble Forecast', x=master_table['SKU'], y=master_table['Ensemble Forecast'], marker_color='#F58518'),
            go.Bar(name='Recommended Order (Units)', x=master_table['SKU'], y=master_table['Order Total Units'], marker_color='#54A24B')
        ])
        fig.update_layout(barmode='group', xaxis_tickangle=-45, height=450, margin=dict(b=120))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("🔍 View Full Master Replenishment Table (All SKUs)", expanded=False):
            st.dataframe(master_table, use_container_width=True, hide_index=True)

# ==========================================
# PAGE 2: STAGE 1 MODEL TRAINING GUI
# ==========================================
elif page == "🧠 Model Training & 6-Fold CV (Stage 1)":
    st.title("🧠 Stage 1: 6-Fold Cross-Validation & Hyperparameter Tuning")
    st.markdown("Upload your multi-year weekly sales history to run Augmented Dickey-Fuller stationarity testing, tune XGBoost & PyTorch LSTM across 6 folds, and compute Inverse-WAPE ensemble weights.")

    hist_file = st.file_uploader("Upload Historical Weekly Sales Dataset (CSV / XLSX)", type=["csv", "xlsx", "xls"])

    if hist_file and st.button("⚙️ Run 6-Fold CV Training & Save Models", type="primary"):
        df_raw = pd.read_csv(hist_file) if hist_file.name.endswith('.csv') else pd.read_excel(hist_file)
        progress_bar = st.progress(0)
        status_text = st.empty()
        run_stage_1_training(df_raw, progress_bar, status_text)
        st.rerun()

# ==========================================
# PAGE 3: DIAGNOSTICS & VALIDATION CHARTS
# ==========================================
elif page == "📊 Model Performance & Diagnostics":
    st.title("📊 6-Fold Validation & Diagnostic Analytics")
    if not model_ready:
        st.info("Train your models in Stage 1 first to view diagnostics.")
        st.stop()

    meta = joblib.load(os.path.join(MODEL_DIR, 'model_metadata.pkl'))
    w = meta["weights"]

    c1, c2, c3 = st.columns(3)
    c1.metric("XGBoost Ensemble Weight", f"{w[0]*100:.1f}%")
    c2.metric("PyTorch LSTM Ensemble Weight", f"{w[1]*100:.1f}%")
    c3.metric("ADF Stationarity p-value", f"{meta['adf_p']:.4f}")

    st.subheader("Master Model Training vs. Testing Diagnostic Table")
    st.dataframe(meta["diag_df"], use_container_width=True, hide_index=True)

    st.subheader("Historical Weekly Sales & 4-Week Moving Average")
    ts = meta["total_sales_series"]
    ma4 = ts.rolling(4).mean()
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=ts.index, y=ts.values, mode='lines+markers', name='Total Weekly Sales'))
    fig_ts.add_trace(go.Scatter(x=ma4.index, y=ma4.values, mode='lines', name='4-Week Moving Average', line=dict(dash='dash', width=3)))
    st.plotly_chart(fig_ts, use_container_width=True)
