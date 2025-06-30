import json

input_file = './api_assessments_export_lower.json'
output_file = './api_assessments_transformed.json'

transformed_data = []

with open(input_file, 'r') as infile:
    for line in infile:
        record = json.loads(line)

        old_answer = record.get('assessment_answer', 'No')
        old_notes = record.get('notes', '')

        new_is_supported = False
        new_caveats = ''

        # Standardize the answer for comparison
        standardized_answer = old_answer.lower().strip()

        if standardized_answer == 'yes':
            new_is_supported = True
            new_caveats = ''
        elif standardized_answer == 'yes (for user accounts)':
            new_is_supported = True
            new_caveats = 'Applicable for user accounts.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        elif standardized_answer == 'yes (with caveats)':
            new_is_supported = True
            new_caveats = 'Supported with limitations.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        elif standardized_answer == 'no':
            new_is_supported = False
            new_caveats = 'Not supported.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        elif standardized_answer == 'partially': # This case was in original logic, keeping it for robustness
            new_is_supported = True
            new_caveats = 'Partially supported.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        elif standardized_answer == 'n/a':
            new_is_supported = False
            new_caveats = 'Not applicable to this API.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        elif standardized_answer == 'n/a (indirectly)':
            new_is_supported = False
            new_caveats = 'Not directly applicable; support is indirect.'
            if old_notes:
                new_caveats += f' Refer to notes for details: {old_notes}'
        else:
            # Fallback for any unexpected values
            new_is_supported = False
            new_caveats = f'Unknown assessment answer: {old_answer}. Original notes: {old_notes}'

        new_record = {
            "api_name": record.get('api_name'),
            "api_domain_name": record.get('api_domain_name'),
            "platform": record.get('platform'),
            "is_endorsed": False, # Default to False for existing entries
            "criterion_category": record.get('criterion_category'),
            "criterion_name": record.get('criterion_name'),
            "is_supported": new_is_supported,
            "caveats": new_caveats,
            "notes": old_notes # Keep original notes for full context
        }
        transformed_data.append(new_record)

with open(output_file, 'w') as outfile:
    for record in transformed_data:
        outfile.write(json.dumps(record) + '\n')
