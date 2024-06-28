import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse

def clear_save_directory():
  """
  Remove all files in directory data/courses/
  """
  path = "data/courses/"
  for filename in os.listdir(path):
    file_path = os.path.join(path, filename)
    os.remove(file_path)

def get_dept_codes():
  """
  Returns list of department codes from CAB website
  """
  # Gets the dropdown element in HTML page that contains list of departments
  url = "https://cab.brown.edu/"
  response = requests.get(url)
  soup = BeautifulSoup(response.content, "html.parser")
  dropdown = soup.find(id="crit-subject")
  # Converts dropdown HTML to list of codes, filtering non-important child elements
  codes = [(child["value"], child.text) for child in dropdown.children 
           if (child.name == "option" and child.attrs["value"])]
  
  # Save codes to a file
  with open("data/dept_codes.txt", "w") as f:
    f.writelines([(code[0] + " " + code[1] + "\n") for code in codes])

  return [code[0] for code in codes]

def generate_dept_payload(srcdb: str, is_ind_study: bool, is_canc: bool, dept_code: str) -> str:
  """
  Generates formatted payload string for retrieving department data
  
  Parameters:
   - srcdb: Which academic term to search
     - ex: '999999' (Any Term), '202410' (Fall 2024), '202420' (Spring 2024)
   - is_ind_study: Whether to include independent study
   - is_canc: Whether to include cancelled courses
   - code: Department code (ex: 'AFRI')
  """
  payload_dict = {
    'other': {
      'srcdb': srcdb
    },
    'criteria': [
      {
        'field': 'subject',
        'value': dept_code
      }
    ]
  }
  if not is_ind_study:
    payload_dict['criteria'].append(
      {'field': 'is_ind_study', 'value': 'N'}
    )
  if not is_canc:
    payload_dict['criteria'].append(
      {'field': 'is_canc', 'value': 'N'}
    )
  # Convert dict to string and parse it
  payload_dict_str = json.dumps(payload_dict)
  return urllib.parse.quote(payload_dict_str)

def generate_course_payload(srcdb: str, code: str, crn: str) -> str:
  """
  Generates formatted payload string for retrieving course data
  
  Parameters:
   - srcdb: Which academic term to search
     - ex: '999999' (Any Term), '202410' (Fall 2024), '202420' (Spring 2024)
   - code: Department code (ex: 'AFRI')
   - crn: Course registration number
  """
  payload_dict = {
    'group': 'code:' + code,
    'key': 'crn:' + crn,
    'srcdb': srcdb,
    'matched': 'crn:' + crn
  }
  # Convert dict to string and parse it
  payload_dict_str = json.dumps(payload_dict)
  return urllib.parse.quote(payload_dict_str)

def get_dept_courses(dept_code: str, term='999999') -> list[dict]:
  """
  Returns list containing all courses associated with the specified department and term
  
  Parameters:
   - dept_code: Department code
   - term: Which academic term to search, default '999999' (Any Term)
  """
  url = (
    "https://cab.brown.edu/api/?page=fose&route=search&is_ind_study=N&is_canc=N&subject="
    + dept_code
  )
  payload = generate_dept_payload(term, False, False, dept_code)
  response = requests.post(url, data=payload)
  dept_dict = response.json()
  return dept_dict['results']

def get_course_details(dept_code: str, crn: str, term='999999') -> dict:
  """
  Returns dictionary containing details for specified course
  
  Parameters:
   - dept_code: Department code
   - crn: Course registration number
   - term: Which academic term to search, default '999999' (Any Term)
  """
  url = "https://cab.brown.edu/api/?page=fose&route=details"
  payload = generate_course_payload(term, dept_code, crn)
  response = requests.post(url, data=payload)
  return response.json()

def get_semester(srcdb: str) -> str:
  """
  Returns the semester of srcdb value
  
  Parameters:
   - srcdb: srcdb value of retrieved course
  """
  # Last two characters of srcdb indicate semester
  semester = srcdb[4:]
  if semester == "10":
    return "Fall"
  elif semester == "15":
    return "Winter"
  elif semester == "20":
    return "Spring"
  elif semester == "00":
    return "Summer"
  else:
    raise Exception(f"Invalid srcdb for semester lookup: {srcdb}")

def organize_all_courses(all_course_data: list[dict]) -> list[dict]:
  """
  Organizes course data by combining entries with same course code,
  and only keeping important fields in the course data. 
  Course codes (ex: CSCI 0150) may appear multiple times in retrieved data 
  because of course sections/labs.
  
  Parameters:
   - course_data: A list of dictionaries that represents the course data to be organized
     - Data structure can be found in examples/dept-courses-data-example.json
  """
  processed_results = []
  # Dictionary that will store pairs as: {course code, index in processed_results}
  seen_courses = {}
  for course in all_course_data:
    if course['code'] not in seen_courses:
      # Found unique course, add to results at index len(seen_courses) (end of results array)
      seen_courses[course['code']] = len(seen_courses)
      processed_results.append(
        {
          'code': course['code'],
          'title': course['title'],
          'semesters': set([get_semester(course['srcdb'])]), # List of semester offerings
          'crns': set([course['crn']]) # List of crns associated with course
        }
      )
    else:
      # Course has already been stored, check if add to semester or crn data
      stored_index = seen_courses[course['code']] # Probably unnecessary but just in case        
      processed_results[stored_index]['semesters'].add(get_semester(course['srcdb']))
      processed_results[stored_index]['crns'].add(course['crn'])

  # Convert sets into lists for JSON
  for result in processed_results:
    result['semesters'] = list(result['semesters'])
    result['crns'] = list(result['crns'])
  return processed_results

def add_course_details(course_data: dict):
  """
  Retrieves individual course details and adds to course data dictionary
  
  Parameters:
  - course_data: Dictionary returned by organize_all_courses
  """
  dept_code = course_data['code'].split(' ')[0]
  crn = course_data['crns'][0] # Choose arbitrary crn
  individual_course_data = get_course_details(dept_code, crn)
  # Only keep relevant keys in course details dictionary
  keys_to_keep = ['seats', 'description', 'registration_restrictions', 'clssnotes', 
                  'resources_critical_review_html', 'resources_syllabus_html', 
                  'resources_materials_html', 'exam_html', 'meeting_html',
                  'instructordetail_html', 'regdemog_json', 'all_sections']
  filtered_data = dict((key, individual_course_data[key]) 
                       for key in keys_to_keep if key in individual_course_data)
  course_data['details'] = filtered_data

def save_all_course_data():
  """
  Runs required functions to retrieve & save course data
  """
  # Get stored department codes
  with open('data/dept_codes.txt', 'r') as f:
    dept_codes = [line.split(" ")[0] for line in f.readlines()]
  
  all_course_data = []
  # Retrieve course data for all departments and combine
  for code in dept_codes:
    dept_courses = get_dept_courses(code)
    print(f"Retrieved {len(dept_courses)} courses from {code}")
    all_course_data.extend(dept_courses)
    
  # Organize course data and write to file
  organized_course_data = organize_all_courses(all_course_data)
  # For progress updates
  course_count = len(organized_course_data)
  for completed, course_data in enumerate(organized_course_data):
    add_course_details(course_data)
    print(f'Saved {completed} of {course_count} courses')
  
  with open('data/courses_complete.json', 'w', encoding='utf-8') as f:
    json.dump(organized_course_data, f, ensure_ascii=False, indent=4)
    
  print(f"Saved data for {len(dept_codes)} departments and "
        f"{course_count} courses to data/courses_complete.json")

if __name__ == "__main__":
  get_dept_codes()
  save_all_course_data()
