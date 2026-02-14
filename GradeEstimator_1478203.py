#---------WEEK 5----------

import json # Importing the json library helps us to read and convert tasks.json file into Python data structures

# 1. Create Task_type class (as requested by the task) and add constructor wuth the following values
class Task_type:
    # Constructor initializes and sets up properties each task type will store
    def __init__(self, name, display_name, tasks_per_semester, maximum_points_per_task):
        self.name = name # Set the internal name of the assignment
        self.display_name = display_name # Set how the assignment should be displayed
        self.tasks_per_semester = tasks_per_semester # Store how many of these tasks exist
        self.maximum_points_per_task = maximum_points_per_task # Store the max points per task

# 2. Parse the tasks.json file
#with open('tasks.json', 'r') as file:
    #data = json.load(file)
try:
    with open('tasks.json', 'r') as file: # Opens tasks.json in read mode
        data = json.load(file) # Converts the JSON file into a Python dictionary
        print("Successfully parsed the tasks.json file") # prints success message
except FileNotFoundError: # if Python can’t find the file it prints an error message
    print("Error: tasks.json file not found. Please ensure it is in the correct directory.")
    data = {"assignment_types": []}

# 3. Create an empty list for storing task types
task_types_list = []

# 4. Iterate through the "assignment type" inside tasks.json and creates class instances
#The loop goes through each assignment type one by one.
for item in data['assignment_types']:

    # Create a new instance of Task_type using data from the JSON
    new_task = Task_type(
        item['name'],
        item['display_name'],
        item['tasks_per_semester'],
        item['max_points_per_submission']
    )
    # Add the newly created object to our list
    task_types_list.append(new_task)

# 5. Calculate total maximum points without hard-coding
total_max_points = 0 # Starting at zero
for task in task_types_list:
    # Calculating and adding same formula for each task to the running total
    total_max_points += (task.tasks_per_semester * task.maximum_points_per_task)

# 6. Prints the final output
# (8*50 + 4*50 + 8*50) = 1000
print(f"Maximum grade you can get for this class is: {total_max_points}")

# # -----------WEEK 4-----------------------
# # --- CLASSES FOR EACH ASSIGNMENT TYPE ---
# class Discussions:
#     # Required properties set to correct values
#     maximum_points_per_task = 50
#     tasks_per_semester = 8
#     display_name = "Discussions"
#
# class Course_projects:
#     maximum_points_per_task = 50
#     tasks_per_semester = 8
#     display_name = "Course Projects"
#
# class Core_assessments:
#     maximum_points_per_task = 50
#     tasks_per_semester = 4
#     display_name = "Core Assessments"
#
# # --- USER IDENTIFICATION ---
# # Collects user input and cleans it using strip and capitalize functions
# first_name = input("Enter your first name: ").strip().capitalize()
# last_name = input("Enter your last name: ").strip().capitalize()
# print(f"Hello {last_name}, {first_name}")
#
# # --- STORING GRADES IN LISTS ---
# # Assigns actual points earned from Units 1, 2, and 3 to each homework list
# total_discussion_points = [50, 50, 50]
# total_course_project_points = [45, 48, 50]  # Unit 2 updated to actual grade of 48
# total_core_assessment_points = [50, 50]  # Core assignments for Units 1 and 3
#
# # --- LOGIC FUNCTION ---
# # Uses class properties to evaluate performance and progress
# def evaluate_performance(points_list, assignment_type):
#     # Moves the "cursor" to a new line and prints 35 "=" symbols in a line as a divider
#     print("\n" + "=" * 35)
#
#     # Step 1: Prints assignment information for each class property
#     print(f"--- {assignment_type.display_name} ---")
#     print(f"Max Points per Task: {assignment_type.maximum_points_per_task}")
#     print(f"Required Tasks per Semester: {assignment_type.tasks_per_semester}")
#
#     # Step 2: Maximum Point Logic
#     all_max_earned = True
#     for point in points_list:
#         # Checks if any individual grade/point is less than the class maximum
#         if point < assignment_type.maximum_points_per_task:
#             all_max_earned = False
#
#     # Step 3: Prints message if maximum points achieved or not per each homework
#     if all_max_earned:
#         print(f"Congrats! You got maximum points for ALL {assignment_type.display_name} homeworks so far!")
#     else:
#         print(f"Unfortunately you did not get maximum points for ALL {assignment_type.display_name} homeworks so far!")
#
#     # Step 4: Prints (points earned so far)/(total possible points) per homework for a term
#     points_earned = sum(points_list)
#     total_possible = assignment_type.tasks_per_semester * assignment_type.maximum_points_per_task
#     print(f"Current {assignment_type.display_name} Progress: {points_earned}/{total_possible} points")
#
# # --- EXECUTION ---
# # Applying the (evaluate_performance) function for every homework types
# evaluate_performance(total_discussion_points, Discussions)
# evaluate_performance(total_course_project_points, Course_projects)
# evaluate_performance(total_core_assessment_points, Core_assessments)
#
# # Last divider printed
# print("\n" + "=" * 35)

# -------------# WEEK 3 # #=-----------------
# #--- USER IDENTIFICATION ---
# # Asks the user's first name and assigns to the variable
# first_name_input = input("Enter your first name: ")
# # Asks the user's last name and assigns to the variable
# last_name_input = input("Enter your last name: ")
#
# # Cleans spaces and capitalizes first letters
# first_name = first_name_input.strip().lower().capitalize()
# last_name = last_name_input.strip().lower().capitalize()
#
# # Greets the user
# print(f"Hello {last_name}, {first_name}")
#
# # Points earned for Unit 1 Discussion
# Unit1_discussion_points = 50
# # Points earned for Unit 1 Course Project
# Unit1_course_project_points = 45
# # Points earned for Unit 1 Core Assessment
# Unit1_core_assessment_points = 50
#
# # Points for Unit 2 Discussion (not actual)
# Unit2_discussion_points = 50
# # Points for Unit 2 Course Project
# Unit2_course_project_points = 48
#
# # --- LISTS ---
# # Stores discussion grades;
# total_discussion_points = [Unit1_discussion_points, Unit2_discussion_points]
# # Stores project grades;
# total_course_project_points = [Unit1_course_project_points, Unit2_course_project_points]
# # Stores core assessment grades;
# total_core_assessment_points = [Unit1_core_assessment_points]
#
# # Sums the points Currently earned in each Unit
# curr_disc = sum(total_discussion_points)
# curr_proj = sum(total_course_project_points)
# curr_core = sum(total_core_assessment_points)
#
# # Per rubric: 8 Discussions, 8 Projects, 4 Core Assessments (50 points each)
# max_disc = 8 * 50
# max_proj = 8 * 50
# max_core = 4 * 50
#
# # # --- DISPLAY OUTPUT ---
# # # Displays current progress vs potential max using String.format
# # print("Currently you have {} points for discussions out of {}".format(curr_disc, max_disc))
# # print("Currently you have {} points for course projects out of {}".format(curr_proj, max_proj))
# # print("Currently you have {} points for core assessments out of {}".format(curr_core, max_core))

# # -------------WEEK 2 ---------------------
# Using f string prints the greeting message
# # With embedded and newly assigned variables (last_name, first_name)
# print(f"Hello {last_name}, {first_name}")
#
# # POINTS EARNED FOR UNIT 1
# # Assigning actual points received for Unit_1_discussion_points variable
# Unit1_discussion_points = 50
#
# # Assigning actual points received for Unit_1_course_project_points variable
# Unit1_course_project_points = 48

# ----------------WEEK 1 ----------------------------
# Asks the user to input his first name and stores the value under variable called first_name
# first_name = input("Please enter your first name: ")
#
# # Asks the user to input his last name and stores the value under variable called last_name
# last_name = input("Please enter your last name: ")
#
# # Prints the full name by combining both first and last name with a space
# print(f"{first_name} {last_name}")