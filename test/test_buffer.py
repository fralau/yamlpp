"""
Test the buffer functions
(for producing export files)
"""
from pathlib import Path
from string import Template


from yamlpp import yamlpp_comp 
from yamlpp.error import YAMLppError
from yamlpp.util import print_yaml

def test_buffer_simple(tmp_path):
    "Simple test of a buffer"

    EXPORT_FILENAME = 'test.txt'

    program = f"""
.do:
    - .open_buffer:
        .name: foo
        .init: "Hello World"

    - .write_buffer:
        .name: foo
        .text: "Hello 2"

    - .save_buffer:
        .name: foo
        .filename: {EXPORT_FILENAME}
"""
    yaml, tree = yamlpp_comp(program, tmp_path)

    out_file = Path(tmp_path) / EXPORT_FILENAME
    assert out_file.is_file()
    with open(out_file) as f:
        result = f.read()
    assert "Hello World" in result
    assert "Hello 2" in result



def test_buffer_complete(tmp_path):
    "Test creation of a buffer"

    EXPORT_FILENAME = 'test.txt'

    template = Template("""
.context:
    meetings:
        - title: Project Kickoff
          date: 2026-01-15
          time: "10:00-11:00"
          location: Room A / Zoom
          participants: Alice, Bob, Carol
          notes: Define scope and milestones
        - title: Design Review
          date: 2026-01-20
          time: "14:00-15:30"
          location: Room B
          participants: Alice, Dave
          notes: Review architecture and risk
        - title: Sprint Planning
          date: 2026-01-22
          time: "09:00-10:30"
          location: Zoom
          participants: Team
          notes: Plan tasks for next sprint

    header: |
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Meetings</title>
            <style>
                body {
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    margin: 2rem;
                    background-color: #f7f7f7;
                }

                h1 {
                    margin-bottom: 1rem;
                }

                table {
                    border-collapse: collapse;
                    width: 100%;
                    background-color: #ffffff;
                }

                th, td {
                    border: 1px solid #cccccc;
                    padding: 0.5rem 0.75rem;
                    text-align: left;
                }

                th {
                    background-color: #f0f0f0;
                }

                tr:nth-child(even) {
                    background-color: #fafafa;
                }

                caption {
                    caption-side: top;
                    text-align: left;
                    font-weight: bold;
                    margin-bottom: 0.5rem;
                }
            </style>
        </head>
        <body>
            <h1>Meetings</h1>

            <table>
                <caption>Upcoming meetings</caption>
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Location / Link</th>
                        <th>Participants</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>



    footer: |
        .       </tbody>
            </table>
        </body>
        </html>

        
.do:
    - .open_buffer:
        .name: myprogram
        .language: HTML
        .init: "{{ header }}"

    - .write_buffer:
        .name: myprogram
        .indent: 1

    - .foreach:
        .values: [m, "{{ meetings }}"]
        .do:
            .write_buffer:
                .name: myprogram
                .text: |
                    <tr>
                        <td>{{ m.title }}</td>
                        <td>{{ m.date }}</td>
                        <td>{{ m.location }}</td>
                        <td>{{ m.participants }}</td>
                        <td>{{ m.notes }}</td>
                    </tr>

    - .write_buffer:
        .name: myprogram
        .indent: -3
        .text: "{{ footer }}"

    - .save_buffer:
        .name: myprogram
        .filename: "$filename"
""") 
    program = template.substitute(filename=EXPORT_FILENAME) 
    yaml, tree = yamlpp_comp(program, tmp_path)
    out_file = Path(tmp_path) / EXPORT_FILENAME
    assert out_file.is_file()
    with open(out_file) as f:
        result = f.read()
    print_yaml(result, "Compiled result")
    