import os
import subprocess
import csv

def analyze_code(file_path):
    # Run pylint analysis
    name = os.path.basename(file_path).split('.')[0]
    report_name = f'{name}_report.txt'
    save_path = os.path.join('static', 'reports', report_name)
    report_path = os.path.abspath(save_path)
    command = f"pylint {file_path} --output-format=text > {report_path}"
    output = subprocess.run(command, shell=True, capture_output=True)
    print(f'Pylint output: {output.stdout.decode()}')
    return report_path

# Example usage:
if __name__ == '__main__':
    file_path = 'server.py'
    report_path = analyze_code(file_path)