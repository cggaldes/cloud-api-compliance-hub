import json

input_file = './data/api_assessments_export_lower.json'

unique_answers = set()

with open(input_file, 'r') as infile:
    for line in infile:
        record = json.loads(line)
        unique_answers.add(record.get('assessment_answer'))

print(sorted(list(unique_answers)))
