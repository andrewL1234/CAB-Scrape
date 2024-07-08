import json

SEPARATOR = '\n\n --- \n\n'

def formatted_json_to_txt():
  """
  Takes the formatted json course data, and converts to a txt file.
  Reorganizes data for more readability. Assumes existence of formatted
  json course data in data/courses_complete_formatted.json.
  """
  with open('data/courses_complete_formatted.json', 'r', encoding='utf-8') as f:
    course_data = json.load(f)

  # Concatenate each course's data into a string to write to the txt file
  course_data_strings = []
  for course in course_data:
    course_string = ""
    course_string += (course['code'] + " - " + course['title'] + '\n')
    course_string += ('Course Description: ' + course['details']['description'] + '\n')
    course_string += ('This course will be offered in the ' + 
                      course['semesters'] + '\n')
    course_string += ('This course will be taught by ' + 
                      course['details']['instructordetail_html'] + '\n')
    course_string += ('This course will meet on ' + 
                      course['details']['meeting_html'] + '\n')
    course_string += ('The final exam for this course will be on ' + 
                      course['details']['exam_html'] + '\n')
    if course['details']['attr_html']:
      course_string += ('This course belongs to the following curricular programs: ' + 
                        course['details']['attr_html'] + '\n')

    # Enrollment info
    course_string += ('Enrollment info: \n')
    if course['details']['seats']:
      course_string += (' - ' + course['details']['seats'] + '\n')
    course_string += (' - Enrollment demographics: ' + course['details']['registration_info'] + '\n')

    # Registration info
    course_string += ('Registration info: \n')
    course_string += (' - Registration requirements: ' + course['details']['registration_restrictions'] + '\n')
    course_string += (' - Grade Mode Options: ' + course['details']['registration_options'] + '\n')
    course_string += (' - Additional registration information:' + course['details']['clssnotes'])

    if len(course_data_strings) == 0: # No separator for first string
      course_data_strings.append(course_string)
    else:
      course_data_strings.append(SEPARATOR + course_string)

  with open('data/courses_complete_txt.txt', 'w', encoding='utf-8') as f:
    f.writelines(course_data_strings)

if __name__ == "__main__":
  formatted_json_to_txt()