import csv
import os
import lstemp as lt

def stack_csv_files(input_files, output_file):
    if not input_files:
        print("No input files provided.")
        return

    # Open the output file in write mode
    with open(output_file, 'w', newline='') as outfile:
        writer = None

        for idx, input_file in enumerate(input_files):
            with open(input_file, 'r') as infile:
                reader = csv.reader(infile)
                headers = next(reader)

                # Write the header only for the first file
                if idx == 0:
                    writer = csv.writer(outfile)
                    writer.writerow(headers)

                for row in reader:
                    writer.writerow(row)

if __name__ == "__main__":
    # List of input CSV files
    input_files = lt.list

    # Output CSV file
    output_file = "total_form.csv"

    # Stack the CSV files
    stack_csv_files(input_files, output_file)

    print(f"CSV files have been stacked into {output_file}")
