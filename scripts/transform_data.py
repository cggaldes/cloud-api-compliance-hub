import json
import argparse

def transform_data(input_file, output_file):
    """
    Transforms assessment data from an old schema to the new schema.
    """
    transformed_data = []

    with open(input_file, 'r') as infile:
        for line in infile:
            record = json.loads(line)

            old_answer = record.get('assessment_answer', 'No')
            old_notes = record.get('notes', '')

            new_is_supported = False
            new_caveats = ''

            standardized_answer = old_answer.lower().strip()

            if standardized_answer == 'yes':
                new_is_supported = True
            elif standardized_answer == 'yes (for user accounts)':
                new_is_supported = True
                new_caveats = 'Applicable for user accounts.'
            elif standardized_answer == 'yes (with caveats)':
                new_is_supported = True
                new_caveats = 'Supported with limitations.'
            elif standardized_answer in ['no', 'n/a', 'n/a (indirectly)']:
                new_is_supported = False
                if standardized_answer == 'n/a':
                    new_caveats = 'Not applicable to this API.'
                elif standardized_answer == 'n/a (indirectly)':
                    new_caveats = 'Not directly applicable; support is indirect.'
                else: # 'no'
                    new_caveats = 'Not supported.'
            elif standardized_answer == 'partially':
                new_is_supported = True
                new_caveats = 'Partially supported.'
            else:
                new_is_supported = False
                new_caveats = f'Unknown assessment answer: {old_answer}.'

            if old_notes and new_caveats:
                 new_caveats += f' Refer to notes for details: {old_notes}'
            elif old_notes:
                new_caveats = old_notes


            new_record = {
                "api_name": record.get('api_name'),
                "api_domain_name": record.get('api_domain_name'),
                "platform": record.get('platform', '').lower(),
                "is_endorsed": record.get('is_endorsed', False),
                "criterion_category": record.get('criterion_category'),
                "criterion_name": record.get('criterion_name'),
                "is_supported": new_is_supported,
                "caveats": new_caveats,
                "notes": old_notes
            }
            transformed_data.append(new_record)

    with open(output_file, 'w') as outfile:
        for record in transformed_data:
            outfile.write(json.dumps(record) + '\n')
    
    print(f"Successfully transformed '{input_file}' and saved to '{output_file}'")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transform assessment JSON data to a new schema.')
    parser.add_argument('input_file', help='The path to the input JSON file.')
    parser.add_argument('output_file', help='The path to the output JSON file.')
    args = parser.parse_args()

    transform_data(args.input_file, args.output_file)