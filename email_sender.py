"""
Email Sender — Snapify Attendance System
Step 5: Send attendance status emails to all registered students.
Uses Python built-in smtplib (no extra dependencies needed).
"""

import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


# ── Default sender ──────────────────────────────────────────────────────────
DEFAULT_SENDER = "subbiahsenthilkumar15@gmail.com"
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587


# ── HTML email template ──────────────────────────────────────────────────────
def _build_html(student_name: str, status: str, class_name: str, date_str: str) -> str:
    status_color  = "#00b894" if status == "Present" else "#e17055"
    status_emoji  = "✅" if status == "Present" else "❌"
    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Attendance Notification</title>
</head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0"
               style="background:#1a1a2e;border-radius:16px;overflow:hidden;
                      box-shadow:0 8px 32px rgba(0,0,0,0.4);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6c63ff,#4a90d9);
                       padding:36px 40px;text-align:center;">
              <div style="font-size:48px;margin-bottom:12px;">🎯</div>
              <div style="color:#ffffff;font-size:22px;font-weight:700;
                          letter-spacing:1px;">Snapify Attendance System</div>
              <div style="color:rgba(255,255,255,0.75);font-size:13px;
                          margin-top:6px;">Automated Attendance Notification</div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <p style="color:#cdd6f4;font-size:17px;margin:0 0 24px;">
                Hey, <strong style="color:#ffffff;">{student_name}</strong>,
              </p>
              <p style="color:#a6adc8;font-size:15px;line-height:1.7;margin:0 0 30px;">
                Your attendance has been recorded for the following session:
              </p>

              <!-- Info card -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#12122a;border-radius:12px;
                            border:1px solid #2a2a4a;margin-bottom:32px;">
                <tr>
                  <td style="padding:24px 28px;">
                    <table width="100%" cellpadding="0" cellspacing="8">
                      <tr>
                        <td style="color:#6c63ff;font-size:12px;font-weight:700;
                                   letter-spacing:1px;text-transform:uppercase;
                                   padding-bottom:4px;">CLASS / PERIOD</td>
                      </tr>
                      <tr>
                        <td style="color:#ffffff;font-size:20px;font-weight:700;
                                   padding-bottom:20px;">{class_name}</td>
                      </tr>
                      <tr>
                        <td style="color:#6c63ff;font-size:12px;font-weight:700;
                                   letter-spacing:1px;text-transform:uppercase;
                                   padding-bottom:4px;">DATE</td>
                      </tr>
                      <tr>
                        <td style="color:#cdd6f4;font-size:16px;
                                   padding-bottom:20px;">{formatted_date}</td>
                      </tr>
                      <tr>
                        <td style="color:#6c63ff;font-size:12px;font-weight:700;
                                   letter-spacing:1px;text-transform:uppercase;
                                   padding-bottom:4px;">ATTENDANCE STATUS</td>
                      </tr>
                      <tr>
                        <td>
                          <span style="display:inline-block;
                                       background:{status_color}20;
                                       color:{status_color};
                                       border:1.5px solid {status_color};
                                       border-radius:8px;
                                       padding:8px 20px;
                                       font-size:18px;font-weight:700;">
                            {status_emoji} {status}
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="color:#a6adc8;font-size:14px;line-height:1.7;margin:0 0 8px;">
                {"Glad you were in class! Keep up the great attendance." if status == "Present"
                  else "If you believe this is an error, please contact your instructor."}
              </p>

              <p style="color:#6c7086;font-size:14px;margin:32px 0 0;">
                Thank You,<br>
                <strong style="color:#a6adc8;">Snapify Attendance System</strong>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#12122a;border-top:1px solid #2a2a4a;
                       padding:20px 40px;text-align:center;">
              <p style="color:#585b70;font-size:12px;margin:0;">
                This is an automated message. Please do not reply to this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_plain(student_name: str, status: str, class_name: str, date_str: str) -> str:
    """Plain text fallback for email clients that don't render HTML."""
    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    return (
        f"Hey, {student_name},\n\n"
        f"You are {status} in '{class_name}' which is held on {formatted_date}.\n\n"
        f"Thank You,\n"
        f"Snapify Attendance System\n\n"
        f"(This is an automated message. Please do not reply.)"
    )


# ── Main function ─────────────────────────────────────────────────────────────
def send_attendance_emails(
    date: str,
    class_name: str,
    sender_email: str = DEFAULT_SENDER,
    sender_password: str = ""
) -> dict:
    """
    Send attendance status emails to all registered students.

    Args:
        date          : Date string 'YYYY-MM-DD'
        class_name    : The class/period name (e.g. 'Maths')
        sender_email  : Gmail address to send from
        sender_password: Gmail App Password (16-char)

    Returns:
        dict with keys: total, sent, failed, details (list of per-student results)
    """
    results = {"total": 0, "sent": 0, "failed": 0, "details": []}

    # 1. Load all registered students ─────────────────────────────────────────
    try:
        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()
        cursor.execute("SELECT roll_number, name, email FROM students ORDER BY name")
        students = cursor.fetchall()  # [(roll, name, email), ...]

        # 2. Load who was present for this date + class ───────────────────────
        if class_name and class_name.lower() != "all":
            cursor.execute(
                "SELECT roll_number FROM attendance WHERE date=? AND class_name=?",
                (date, class_name)
            )
        else:
            cursor.execute(
                "SELECT roll_number FROM attendance WHERE date=?",
                (date,)
            )
        present_rolls = {row[0] for row in cursor.fetchall()}
        conn.close()
    except Exception as db_err:
        results["details"].append({"name": "DB Error", "email": "", "status": "error",
                                    "message": str(db_err)})
        return results

    if not students:
        results["details"].append({"name": "—", "email": "", "status": "error",
                                    "message": "No registered students found in database."})
        return results

    results["total"] = len(students)

    # 3. Connect to Gmail SMTP ─────────────────────────────────────────────────
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
    except smtplib.SMTPAuthenticationError:
        results["details"].append({
            "name": "SMTP Auth Error", "email": sender_email,
            "status": "error",
            "message": (
                "Authentication failed. Make sure you are using a Gmail App Password, "
                "not your regular Gmail password. Go to "
                "https://myaccount.google.com/apppasswords to generate one."
            )
        })
        return results
    except Exception as smtp_err:
        results["details"].append({
            "name": "SMTP Connection Error", "email": "",
            "status": "error",
            "message": str(smtp_err)
        })
        return results

    # 4. Send email to each student ────────────────────────────────────────────
    for roll, name, email in students:
        if not email or "@" not in email:
            results["failed"] += 1
            results["details"].append({
                "name": name, "email": email or "—",
                "status": "skipped",
                "message": "No valid email address on record."
            })
            continue

        status = "Present" if roll in present_rolls else "Absent"
        subject = f"Attendance: {status} | {class_name} | {date}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Snapify Attendance <{sender_email}>"
        msg["To"]      = email

        msg.attach(MIMEText(_build_plain(name, status, class_name, date), "plain"))
        msg.attach(MIMEText(_build_html(name, status, class_name, date), "html"))

        try:
            server.sendmail(sender_email, email, msg.as_string())
            results["sent"] += 1
            results["details"].append({
                "name": name, "email": email,
                "status": status.lower(),   # "present" | "absent"
                "message": "Email sent successfully."
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "name": name, "email": email,
                "status": "error",
                "message": str(e)
            })

    try:
        server.quit()
    except Exception:
        pass

    return results
