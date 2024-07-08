import json
from bs4 import BeautifulSoup
import re
import pandas as pd
pd.options.display.max_columns = 80
pd.options.display.max_rows = 80

# Constants
RELEVANT_KEY_MAPPINGS = {
  'code': 'course_code',
  'title': 'course_title',
  'semesters': 'course_semester_offerings',
  'details_key': 'id',
  'details_cart_opts': 'grade_modes',
  # 'details_section': 'section',
  'details_seats': 'enrollment_limit',
  'details_description': 'course_description', 
  'details_registration_restrictions': 'registration_restrictions', 
  'details_clssnotes': 'additional_information',
  'details_attr_html': 'curricular_programs', 
  'details_exam_html': 'exam_datetime', 
  'details_meeting_html': 'course_meeting_time', 
  'details_instructordetail_html': 'instructor_information', 
  'details_regdemog_json': 'registration_demographics', 
}

# Helper function
def combine_with_and(strings):
  """
  Takes a list of strings, combine them into one string with commas
  """
  if not strings:
      return ""
  elif len(strings) == 1:
      return strings[0]
  elif len(strings) == 2:
      return f"{strings[0]} and {strings[1]}"
  else:
      return f"{', '.join(strings[:-1])}, and {strings[-1]}"

def format_registration_demographics_field(reg_demog):
  """
  Converts the scraped regdemog_json field into a format that is more easily understandable.
  Assumes that the regdemog_json field is a string representing JSON data.
  """
  # Store the abbreviations that CAB uses
  abbreviations = {
    "FY": "First Year", "So": "Sophomore", "Jr": "Junior", 
    "Sr": "Senior", "Gr": "Graduate Level", "Oth": "Other"
  }
  if reg_demog:
    # Read data as dictionary
    reg_dict = json.loads(reg_demog)

    # Loop over dictionary and add to list
    result_list = []
    for key, value in reg_dict.items():
      assert key in abbreviations
      result_list.append(f"{abbreviations[key]}: {value}")

    result_str = ', '.join(result_list)
    return result_str

def format_grade_modes_field(grade_modes):
  """
  Converts the scraped cart_opts field into a format that is more easily understandable.
  Assumes that the cart_opts field is a string representing JSON data.
  """
  if grade_modes:
    # Read data as dictionary
    cart_dict = json.loads(grade_modes)
    # Get the grade modes from dictionary
    reg_options = [option['label'] for option in cart_dict['grade_mode']['options']]
    
    result_str = ', '.join(reg_options)
    return result_str

def format_sections_field(all_sections):
  """
  Converts the scraped 'all_sections' field into a format that is more easily understandable.
  """
  if all_sections:
    all_sections = all_sections.strip()
    all_sections = all_sections.replace('Section # CRN Meets Instructor ', '').replace(' VIEW CALENDAR', '')
  
  return all_sections

def extract_exam_date(exam_info):
  if exam_info:
    # Remove whitespace characters
    exam_info = exam_info.replace('&#160;', ' ')

    # Define the regex pattern to capture the substring including "Exam Date: "
    pattern = r"(Exam Date: .*?) Exam Group: "
  
    # Search for the pattern in the text
    match = re.search(pattern, exam_info)
  
    if match:
        return match.group(1)  # Return the captured group (including "Exam Date: ")
    else:
        return None  # Return None if the pattern is not found

def format_html_fields(to_format):
  """
  Removes html tags from the specified string, and returns formatted string.
  """
  if to_format:
    soup = BeautifulSoup(to_format, 'html.parser')
    contains_html = bool(soup.find())
    if contains_html:
      parsed_text = soup.get_text(separator=' ', strip=True)

      # Replace non-breaking spaces with regular spaces
      cleaned_text = parsed_text.replace('\u00a0', ' ')
      return cleaned_text
    else:
      return to_format

def format_course(course):
  """ 
  Takes in a DataFrame row representing a course and formats it.
  """
  course['course_semester_offerings'] = combine_with_and(course['course_semester_offerings'])
  course['crns'] = combine_with_and(course['crns'])
  course['grade_modes'] = format_grade_modes_field(course['grade_modes'])
  course['registration_demographics'] = format_registration_demographics_field(course['registration_demographics'])
  course['all_sections'] = format_sections_field(course['all_sections'])
  course['exam_info'] = extract_exam_date(course['exam_info'])

  # For some reason using .apply does not work ??
  for index in course.index:
    course[index] = format_html_fields(course[index])

def format_saved_course_data_df():
  """
  Formats saved course data.
  """
  # Assuming course data has already been scraped, read in the file
  with open('data/courses_complete.json', 'r', encoding='utf-8') as f:
    course_data = json.load(f)
  
  # Convert data to DataFrame
  course_df = pd.json_normalize(course_data, sep='_')

  # First, only keep relevant keys and rename them
  course_df = course_df[RELEVANT_KEY_MAPPINGS.keys()]
  course_df.rename(columns=RELEVANT_KEY_MAPPINGS, inplace=True)

  # Replace empty string with None (for SQL DB)
  course_df.replace({"": None}, inplace=True)

  # Format
  course_df.apply(format_course, axis=1)
  
  # Write back to file
  course_df.to_json('data/courses_complete_formatted_separated.json', force_ascii=False)
  course_df.to_json('data/courses_complete_formatted.json', orient='records', force_ascii=False)

def format_saved_course_data():
  """
  Format saved course data without DataFrame (does not work)
  """
  # Assuming course data has already been scraped, read in the file
  with open('data/courses_complete.json', 'r', encoding='utf-8') as f:
    course_data = json.load(f)
  for course in course_data:
    # First update all empty fields
    course['details'] = {key: None if value == '' else value
                         for key, value in course['details'].items()}

    # First remove all HTML tags
    course['details'] = {key: format_html_fields(value) for key, value in course['details'].items()}
    # Then format individual fields
    format_registration_info_field(course)
    format_registration_options_field(course)
    format_sections_field(course)
    course['semesters'] = combine_with_and(course['semesters'])
    course['crns'] = combine_with_and(course['crns'])
    # if course['details']['meeting_html'] != None:
    #   course['details']['meeting_html'] = replace_days(course['details']['meeting_html'])
    if course['details']['exam_html']:
      course['details']['exam_html'] = extract_exam_date(course['details']['exam_html'])

  # Write back to file
  with open('data/courses_complete_formatted.json', 'w', encoding='utf-8') as f:
    json.dump(course_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
  format_saved_course_data_df()
