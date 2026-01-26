print("hello dear ne")

# Asks the user's first name and assigns to the variable
first_name_input = input("Enter your first name: ")

# Asks the user's first name and assigns to the variable
last_name_input = input("Enter your last name: ")

# Removes spaces before/after first name, converts to lowercase
# Capitalizes only the first letter and assigns to a variable first_name
first_name = first_name_input.strip().lower().capitalize()

# Removes spaces before/after last name, converts to lowercase
# Capitalizes only the first letter and assigns to a variable called last_name
last_name = last_name_input.strip().lower().capitalize()

# Using f string prints the greeting message
# With embedded and newly assigned variables (last_name, first_name)
print(f"Hello {last_name}, {first_name}")

# POINTS EARNED FOR UNIT 1
# Assigning actaul points received for Unit_1_discussion_points variable
Unit1_discussion_points = 50

# Assigning actual points received for Unit_1_course_project_points variable
Unit1_course_project_points = 48

# Assigning non-actual points for Unit_1_core_assessment_points variable
Unit1_core_assesment_points = 50

# Assigning maximum possible points for the task_maximum_points variable
task_maximum_points = 50

# Calculating the total_points earned for Unit 1 using above variables
total_points = (
    Unit1_discussion_points
    + Unit1_course_project_points
    + Unit1_core_assesment_points
)

# Print the value of total points earned using f string
print(f"Total Points: {total_points}")

# Checking whether maximum points were earned for Unit 1 discussion
print(
    "Got maximum points for Unit 1 discussion?",
    Unit1_discussion_points == task_maximum_points
)

# Check whether maximum points were earned for Unit 1 course project
print(
    "Got maximum points for Unit 1 course project?",
    Unit1_course_project_points == task_maximum_points
)

# Check whether maximum points were earned for Unit 1 core assessment
print(
    "Got maximum points for Unit 1 core assessment?",
    Unit1_core_assesment_points == task_maximum_points
)
print("hello")
# Updated Jan 25
# Force Push at 9:15PM
#Final sync