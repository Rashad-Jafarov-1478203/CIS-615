# CIS615 Coursework - Python Programming

This repository contains my assignments and projects for the CIS615 course. 

## 🐍 Main Project
* **[GradeEstimator_1478203.py](GradeEstimator_1478203.py)**: This is the primary Python script used throughout the semester for grade estimation.

# Grade Estimator Application

This Python application calculates Rashad Jafarov's current grade based on task information from a JSON file and grades from a CSV file. 
The code helps to estimate the total grades and Letter Grade if no submission was made or if maximum points were earned for the last 2 homeworks of week 8.
---
## Files Used
- `tasks.json` – Contains task names and maximum points for each task.
- `grades_0.csv` – Contains grades for all tasks, assuming Unit 8 grades are **0**.
- `grades_50.csv` – Contains grades for all tasks, assuming Unit 8 grades are **50**.
---
## How It Works
1. The program reads `tasks.json` to get the maximum points for each task.
2. It reads a CSV file (`grades_0.csv` or `grades_50.csv`) to get the earned grades.
3. It calculates:
   - Total points earned
   - Maximum possible points
   - Percentage
   - Letter grade
4. It displays all the above information to the user.

## How to Run

1. Open a terminal prompt.
2. Navigate to the project folder.
3. Run the Python script:

```bash
python GradeEstimator_ID.py

## 📂 Repository Contents

### 📄 [Resumes/](./Resumes/)
Contains professional documentation and my current resume:
* **resume.pdf**: My professional resume uploaded for the data analyst position.

### 🖼️ [Unit 2/]
Contains submission requirements for the first unit:
* **Running_Code_Screenshot.jpg**: A screenshot showing the successful execution of the Grade Estimator script.
