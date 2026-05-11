from flask import Flask, render_template, request, Response, jsonify
import sqlite3
from datetime import datetime
import csv
import io
import os
import json
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

# ── Parse teacher email from CLI args ──
parser = argparse.ArgumentParser(description='Attendance Dashboard')
parser.add_argument('--teacher', type=str, default='', help='Teacher email for data isolation')
args, _ = parser.parse_known_args()
TEACHER_EMAIL = args.teacher

# ── Database migration: ensure table has correct schema ──
def migrate_db():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    # ── Migrate students table: add teacher_email if missing ──
    cursor.execute("PRAGMA table_info(students)")
    student_cols = [col[1] for col in cursor.fetchall()]
    if student_cols and 'teacher_email' not in student_cols:
        cursor.execute("ALTER TABLE students RENAME TO students_old")
        cursor.execute("CREATE TABLE students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")
        cursor.execute("INSERT OR IGNORE INTO students (roll_number, name, phone, email, teacher_email) SELECT roll_number, name, phone, email, '' FROM students_old")
        cursor.execute("DROP TABLE students_old")
        conn.commit()
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")

    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'")
    result = cursor.fetchone()

    if result:
        table_sql = result[0]
        if 'roll_number' not in table_sql or 'UNIQUE(roll_number,date,class_name' not in table_sql.replace(' ', ''):
            cursor.execute("PRAGMA table_info(attendance)")
            columns = [col[1] for col in cursor.fetchall()]
            has_class_col = 'class_name' in columns
            has_roll_col = 'roll_number' in columns

            cursor.execute("ALTER TABLE attendance RENAME TO attendance_old")
            cursor.execute("CREATE TABLE attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")
            if has_roll_col and has_class_col:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT COALESCE(roll_number, ''), name, COALESCE(class_name, ''), time, date FROM attendance_old")
            elif has_class_col:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, COALESCE(class_name, ''), time, date FROM attendance_old")
            else:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, '', time, date FROM attendance_old")
            cursor.execute("DROP TABLE attendance_old")
            conn.commit()
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")
        conn.commit()
    conn.close()

migrate_db()

@app.route('/')
def index():
    # Get all unique class names for the dropdown (filtered by teacher)
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('index.html', selected_date='', selected_class='', classes=classes, no_data=False, teacher_email=TEACHER_EMAIL)

@app.route('/attendance', methods=['POST'])
def attendance():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    # Get all unique class names for the dropdown (filtered by teacher)
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]

    # Filter by date, class, and teacher
    if selected_class and selected_class != 'All':
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ? ORDER BY name",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND teacher_email = ? ORDER BY class_name, name",
                       (formatted_date, TEACHER_EMAIL))

    attendance_data = cursor.fetchall()
    conn.close()

    if not attendance_data:
        return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                               classes=classes, no_data=True, teacher_email=TEACHER_EMAIL)

    return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                           classes=classes, attendance_data=attendance_data, teacher_email=TEACHER_EMAIL)

@app.route('/delete_attendance', methods=['POST'])
def delete_attendance():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    if not selected_date:
        return "No date selected", 400

    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    # Filter deletion by date, class, and teacher
    if selected_class and selected_class != 'All':
        cursor.execute("DELETE FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ?",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("DELETE FROM attendance WHERE date = ? AND teacher_email = ?",
                       (formatted_date, TEACHER_EMAIL))
    
    conn.commit()

    # Get all unique class names for the dropdown (filtered by teacher)
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                           classes=classes, no_data=True, teacher_email=TEACHER_EMAIL)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    if not selected_date:
        return "No date selected", 400

    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    if selected_class and selected_class != 'All':
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ? ORDER BY name",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND teacher_email = ? ORDER BY class_name, name",
                       (formatted_date, TEACHER_EMAIL))

    attendance_data = cursor.fetchall()
    conn.close()

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll Number', 'Name', 'Class/Period', 'Time', 'Date'])
    for row in attendance_data:
        writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    class_suffix = f"_{selected_class}" if selected_class and selected_class != 'All' else ""
    filename = f"attendance_{formatted_date}{class_suffix}.csv"
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/email_config', methods=['GET'])
def get_email_config():
    """Return saved email sender credentials (if any)."""
    config_path = os.path.join(os.path.dirname(__file__), 'email_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            # Default sender to teacher email
            if not data.get('sender_email'):
                data['sender_email'] = TEACHER_EMAIL
            return jsonify(data)
    return jsonify({'sender_email': TEACHER_EMAIL, 'sender_password': ''})


@app.route('/send_emails', methods=['POST'])
def send_emails():
    """Bulk email: send Present/Absent status to every registered student."""
    date            = request.form.get('date', '').strip()
    class_name      = request.form.get('class_name', '').strip()
    sender_email    = request.form.get('sender_email', '').strip()
    sender_password = request.form.get('sender_password', '').strip()

    if not date:
        return jsonify({'error': 'Date is required.'}), 400
    if not sender_email:
        return jsonify({'error': 'Sender Gmail is required.'}), 400
    if not sender_password:
        return jsonify({'error': 'Gmail App Password is required.'}), 400

    conn   = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    # All registered students with emails (filtered by teacher)
    cursor.execute("SELECT roll_number, name, email FROM students WHERE email IS NOT NULL AND email != '' AND teacher_email = ?", (TEACHER_EMAIL,))
    all_students = cursor.fetchall()  # [(roll, name, email), ...]

    # Who was present for this date + class?
    if class_name and class_name != 'All':
        cursor.execute(
            "SELECT roll_number FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ?",
            (date, class_name, TEACHER_EMAIL)
        )
    else:
        cursor.execute("SELECT roll_number FROM attendance WHERE date = ? AND teacher_email = ?", (date, TEACHER_EMAIL))
    present_rolls = {row[0] for row in cursor.fetchall()}
    conn.close()

    if not all_students:
        return jsonify({'error': 'No registered students with email addresses found.'}), 404

    period_label = class_name if class_name and class_name != 'All' else 'All Periods'

    # ── Open SMTP connection once ─────────────────────────────────────────
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
        # ✅ Save credentials so the user doesn't have to re-enter them
        config_path = os.path.join(os.path.dirname(__file__), 'email_config.json')
        with open(config_path, 'w') as f:
            json.dump({'sender_email': sender_email, 'sender_password': sender_password}, f)
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'total': 0, 'sent': 0, 'failed': 0,
            'details': [{'name': '', 'email': '', 'status': 'error',
                         'message': '❌ Gmail authentication failed. Make sure you are using an App Password '
                                    '(not your regular password) and that 2-Step Verification is enabled.'}]
        }), 200
    except Exception as e:
        return jsonify({
            'total': 0, 'sent': 0, 'failed': 0,
            'details': [{'name': '', 'email': '', 'status': 'error', 'message': str(e)}]
        }), 200

    # ── Send one email per student ────────────────────────────────────────
    details = []
    sent = failed = 0

    for roll, name, email in all_students:
        is_present = roll in present_rolls
        status_word  = 'Present ✅' if is_present else 'Absent ❌'
        status_color = '#2ecc71'    if is_present else '#e74c3c'
        bg_accent    = 'rgba(46,204,113,0.08)' if is_present else 'rgba(231,76,60,0.08)'

        html_body = f"""
        <div style="font-family:Inter,Arial,sans-serif;background:#0f1117;padding:32px;max-width:560px;margin:auto;">
          <h2 style="color:#6c63ff;margin-bottom:4px;">📊 Attendance Report</h2>
          <p style="color:#8b8da3;margin-top:0;font-size:13px;">
            {date} &nbsp;·&nbsp; {period_label}
          </p>
          <div style="background:{bg_accent};border:1px solid {status_color}33;
                      border-radius:12px;padding:24px 28px;margin:20px 0;text-align:center;">
            <div style="font-size:13px;color:#8b8da3;margin-bottom:6px;">Hello, <strong style="color:#e8e8f0;">{name}</strong></div>
            <div style="font-size:38px;margin:8px 0;">{('✅' if is_present else '❌')}</div>
            <div style="font-size:22px;font-weight:700;color:{status_color};">{status_word}</div>
            <div style="font-size:13px;color:#8b8da3;margin-top:8px;">
              Your attendance has been {'recorded' if is_present else 'marked as absent'} for
              <strong style="color:#e8e8f0;">{period_label}</strong> on <strong style="color:#e8e8f0;">{date}</strong>.
            </div>
          </div>
          <p style="color:#8b8da3;font-size:11px;margin-top:20px;">
            Roll No: {roll} &nbsp;·&nbsp; Generated by Snapify Attendance System
          </p>
        </div>
        """

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Attendance – {date} | {period_label} | {status_word}'
            msg['From']    = sender_email
            msg['To']      = email
            msg.attach(MIMEText(html_body, 'html'))
            server.sendmail(sender_email, [email], msg.as_string())
            details.append({'name': name, 'email': email,
                            'status': 'present' if is_present else 'absent',
                            'message': f'Email sent successfully'})
            sent += 1
        except Exception as e:
            details.append({'name': name, 'email': email, 'status': 'error', 'message': str(e)})
            failed += 1

    server.quit()

    return jsonify({'total': len(all_students), 'sent': sent, 'failed': failed, 'details': details})


# ── Email Report ────────────────────────────────────────────────────────────
@app.route('/send_email_report', methods=['POST'])
def send_email_report():
    selected_date  = request.form.get('selected_date', '')
    selected_class = request.form.get('selected_class', '')
    recipient      = request.form.get('recipient_email', '').strip()

    if not selected_date:
        return jsonify({'error': 'No date selected'}), 400
    if not recipient:
        return jsonify({'error': 'No recipient email provided'}), 400

    sender   = os.environ.get('SMTP_SENDER', '')
    password = os.environ.get('SMTP_PASSWORD', '')
    if not sender or not password:
        return jsonify({'error': 'SMTP credentials not configured (set SMTP_SENDER and SMTP_PASSWORD env vars)'}), 500

    # ── Query attendance (filtered by teacher) ──
    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    conn   = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    if selected_class and selected_class != 'All':
        cursor.execute(
            "SELECT roll_number, name, class_name, time, date FROM attendance "
            "WHERE date = ? AND class_name = ? AND teacher_email = ? ORDER BY name",
            (formatted_date, selected_class, TEACHER_EMAIL)
        )
    else:
        cursor.execute(
            "SELECT roll_number, name, class_name, time, date FROM attendance "
            "WHERE date = ? AND teacher_email = ? ORDER BY class_name, name",
            (formatted_date, TEACHER_EMAIL)
        )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'error': 'No attendance data for the selected filters'}), 404

    # ── Build HTML email body ─────────────────────────────────────────────
    period_label = selected_class if selected_class and selected_class != 'All' else 'All Periods'
    table_rows   = ''.join(
        f'<tr style="background:{ "#1e2130" if i % 2 == 0 else "#181c2b" };">' 
        f'<td style="padding:10px 14px;">{i+1}</td>'
        f'<td style="padding:10px 14px;"><strong>{r[0]}</strong></td>'
        f'<td style="padding:10px 14px;">{r[1]}</td>'
        f'<td style="padding:10px 14px;">{r[2]}</td>'
        f'<td style="padding:10px 14px;">{r[3]}</td>'
        f'<td style="padding:10px 14px;">{r[4]}</td>'
        '</tr>'
        for i, r in enumerate(rows)
    )

    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#0f1117;padding:32px;">
      <h2 style="color:#6c63ff;margin-bottom:4px;">📊 Attendance Report</h2>
      <p style="color:#8b8da3;margin-top:0;">
        Date: <strong style="color:#e8e8f0;">{formatted_date}</strong> &nbsp;·&nbsp;
        Period: <strong style="color:#e8e8f0;">{period_label}</strong>
      </p>
      <table style="width:100%;border-collapse:collapse;background:#1a1d27;border-radius:10px;overflow:hidden;">
        <thead>
          <tr style="background:rgba(108,99,255,0.15);">
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">#</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Roll No</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Name</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Class / Period</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Time</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Date</th>
          </tr>
        </thead>
        <tbody style="color:#e8e8f0;font-size:14px;">
          {table_rows}
        </tbody>
      </table>
      <p style="color:#8b8da3;font-size:12px;margin-top:20px;">
        Total students present: <strong style="color:#6c63ff;">{len(rows)}</strong><br>
        Generated by Snapify Attendance System
      </p>
    </div>
    """

    # ── Send via Gmail SMTP ───────────────────────────────────────────────
    try:
        msg                     = MIMEMultipart('alternative')
        msg['Subject']          = f'Attendance Report – {formatted_date} ({period_label})'
        msg['From']             = sender
        msg['To']               = recipient
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())

        return jsonify({'success': True, 'message': f'Report sent to {recipient}'})
    except smtplib.SMTPAuthenticationError:
        return jsonify({'error': 'SMTP authentication failed. Check SMTP_SENDER and SMTP_PASSWORD.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Student List ────────────────────────────────────────────────────────────
@app.route('/students')
def students_list():
    """Show all registered students with optional search (filtered by teacher)."""
    search = request.args.get('q', '').strip()

    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")

    if search:
        like = f'%{search}%'
        cursor.execute(
            "SELECT roll_number, name, phone, email FROM students "
            "WHERE teacher_email = ? AND (roll_number LIKE ? OR name LIKE ? OR phone LIKE ? OR email LIKE ?) "
            "ORDER BY roll_number",
            (TEACHER_EMAIL, like, like, like, like)
        )
    else:
        cursor.execute("SELECT roll_number, name, phone, email FROM students WHERE teacher_email = ? ORDER BY roll_number", (TEACHER_EMAIL,))

    students = cursor.fetchall()
    conn.close()
    return render_template('students.html', students=students, search=search, teacher_email=TEACHER_EMAIL)


if __name__ == '__main__':
    app.run(debug=True)
