import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# CONFIGURATION
# In production, use os.getenv("EMAIL_USER")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "sick7bestemv14@gmail.com" # <--- REPLACE THIS
SENDER_PASSWORD = "olnrvvvobgqcqfqz"   # <--- REPLACE THIS

def send_event_email(user_email, event_data):
    """
    Sends an HTML email to the user with the event details.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Event Found: {event_data.get('title', 'Cool Event')}"
        msg["From"] = SENDER_EMAIL
        msg["To"] = user_email

        # HTML Content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #2563EB; padding: 20px; text-align: center; color: white;">
                    <h1 style="margin: 0;">SocialSync Event</h1>
                    <p>We found something matching your vibe!</p>
                </div>
                
                <div style="padding: 20px;">
                    <h2 style="color: #1F2937;">{event_data.get('title')}</h2>
                    <p><strong>📅 Date:</strong> {event_data.get('date')}</p>
                    <p><strong>📍 Location:</strong> {event_data.get('location')}</p>
                    <p><strong>💰 Cost:</strong> {event_data.get('cost')}</p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-style: italic;">"{event_data.get('description')}"</p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{event_data.get('url')}" 
                           style="background-color: #10B981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                           Check Full Details
                        </a>
                    </div>
                </div>
                
                <div style="background-color: #f9fafb; padding: 15px; text-align: center; font-size: 12px; color: #6b7280;">
                    <p>Sent by SocialSync AI Agent.</p>
                </div>
            </div>
        </body>
        </html>
        """

        part = MIMEText(html_content, "html")
        msg.attach(part)

        # Sending the email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, user_email, msg.as_string())
        server.quit()
        
        return True, "Email sent successfully"

    except Exception as e:
        print(f"Email Error: {e}")
        return False, str(e)