import os
import subprocess

def pyflakes_analyze(file_path):
    # Run pyflakes command
    result = subprocess.run(['pyflakes', file_path], capture_output=True, text=True)
    
    # Store pyflakes output in report.txt
    report_path = os.path.join(os.path.dirname(file_path), 'pyflakes_report.txt')
    with open(report_path, 'w') as report_file:
        report_file.write(result.stdout)
    
    return report_path


if __name__ == '__main__':
    # Test pyflakes_analyze function
    print(pyflakes_analyze('server.py'))