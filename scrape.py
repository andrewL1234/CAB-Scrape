import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse

def generate_dept_payload(srcdb: str, is_ind_study: bool, is_canc: bool, code: str) -> str:
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
        'value': code
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

def get_classes(course_code):
  url = (
    "https://cab.brown.edu/api/?page=fose&route=search&is_ind_study=N&is_canc=N&subject="
    + course_code
  )
  payload = generate_dept_payload('999999', False, False, course_code)
  response = requests.post(url, data=payload)
  return response.json()

def get_course_codes():
  """
  Returns list of course codes from CAB website
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
  with open("data/course_codes.txt", "w") as f:
    f.writelines([(code[0] + ", " + code[1] + "\n") for code in codes])

  return [code[0] for code in codes]

def code_to_semester(result):
  """
  Convert a course code to a semester
  """
  code = result["srcdb"]
  subcode = code[4:]
  if subcode == "10":
    return "Fall"
  elif subcode == "15":
    return "Winter"
  elif subcode == "20":
    return "Spring"
  elif subcode == "00":
    return "Summer"
  else:
    raise Exception("Invalid course code: " + code)

def filter_results(results):
  """
  Removes duplicate courses
  """
  seen_courses = set()
  results_filtered = []
  for result in results:
    # Course codes (ex: CSCI 0150) may appear multiple times in retrieved data because of course sections/labs
    if result["code"] not in seen_courses:
        seen_courses.add(result["code"])
        semesters = list(
          set(
            map(
              code_to_semester,
              filter(lambda x: x["code"] == result["code"], results),
            )
          )
        )
        results_filtered.append(
          {
            "code": result["code"],
            "title": result["title"],
            "semesters": semesters,
            "crn": result["crn"],
          }
        )

  return results_filtered

def save_all_class_data():
  codes = get_course_codes()
  all_results = []
  for code in codes:
    data = get_classes(code)
    results = data["results"]
    fixed_results = filter_results(results)
    all_results.extend(fixed_results)

    with open("data/courses/" + code + ".json", "w") as f:
      json.dump(fixed_results, f, indent=4)
    print(code, ":", len(data["results"]), "classes")

  with open("data/courses_complete.json", "w") as f:
    json.dump(all_results, f, indent=4)
  print("Saved data for " + str(len(codes)) + " departments")

def clear_save_directory():
  """
  Remove all files in directory data/courses/
  """
  path = "data/courses/"
  for filename in os.listdir(path):
    file_path = os.path.join(path, filename)
    os.remove(file_path)

if __name__ == "__main__":
  data = get_classes("AFRI")
  with open("examples/dept-data-example.json", "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
