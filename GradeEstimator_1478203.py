# --- USER IDENTIFICATION ---
# Asks the user's first name and assigns to the variable
first_name_input = input("Enter your first name: ")
# Asks the user's last name and assigns to the variable
last_name_input = input("Enter your last name: ")

# Cleans spaces and capitalizes first letters
first_name = first_name_input.strip().lower().capitalize()
last_name = last_name_input.strip().lower().capitalize()

# Greets the user
print(f"Hello {last_name}, {first_name}")

# Points earned for Unit 1 Discussion
Unit1_discussion_points = 50
# Points earned for Unit 1 Course Project
Unit1_course_project_points = 45
# Points earned for Unit 1 Core Assessment
Unit1_core_assessment_points = 50

# Points for Unit 2 Discussion (not actual)
Unit2_discussion_points = 50
# Points for Unit 2 Course Project
Unit2_course_project_points = 48

# --- LISTS ---
# Stores discussion grades;
total_discussion_points = [Unit1_discussion_points, Unit2_discussion_points]
# Stores project grades;
total_course_project_points = [Unit1_course_project_points, Unit2_course_project_points]
# Stores core assessment grades;
total_core_assessment_points = [Unit1_core_assessment_points]

# Sums the points Currently earned in each Unit
curr_disc = sum(total_discussion_points)
curr_proj = sum(total_course_project_points)
curr_core = sum(total_core_assessment_points)

# Per rubric: 8 Discussions, 8 Projects, 4 Core Assessments (50 points each)
max_disc = 8 * 50
max_proj = 8 * 50
max_core = 4 * 50

# --- DISPLAY OUTPUT ---
# Displays current progress vs potential max using String.format
print("Currently you have {} points for discussions out of {}".format(curr_disc, max_disc))
print("Currently you have {} points for course projects out of {}".format(curr_proj, max_proj))
print("Currently you have {} points for core assessments out of {}".format(curr_core, max_core))