# Add this to functions_email.py (create this file if it doesn't exist)

from config import *
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_settings():
    # Return a dictionary with your email settings
    return {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': '587',
        'smtp_username': 'innov8gpt@gmail.com',
        'smtp_password': 'emhfzanfshusuhla', # Replace with actual app password
        'smtp_from_email': 'innov8gpt@gmail.com',
        'app_url': 'https://innov8gpt-app.azurewebsites.net',
    }

def send_group_invitation_email(recipient_email, recipient_name, group_name, inviter_name, inviter_role, group_id, custom_message=None):
    """
    Send an email invitation to join a group.
    
    Args:
        recipient_email: Email address of the invited user
        recipient_name: Display name of the invited user
        group_name: Name of the group/channel
        inviter_name: Name of the person sending the invitation
        inviter_role: Role of the inviter (Owner, Admin, Document Manager)
        group_id: ID of the group for generating the join link
        custom_message: Optional custom message from the inviter
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Get email settings from application settings
        settings = get_settings()
        smtp_server = settings.get('smtp_server', os.getenv('SMTP_SERVER'))
        smtp_port = settings.get('smtp_port', os.getenv('SMTP_PORT'))
        smtp_username = settings.get('smtp_username', os.getenv('SMTP_USERNAME'))
        smtp_password = settings.get('smtp_password', os.getenv('SMTP_PASSWORD'))
        from_email = settings.get('smtp_from_email', os.getenv('SMTP_FROM_EMAIL'))
        app_url = settings.get('app_url', os.getenv('APP_URL'))
        
        # Check if email settings are configured
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, from_email]):
            print("Email settings not configured. Skipping invitation email.")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Invitation to join {group_name} channel in {settings.get('app_title', 'Simple Chat')}"
        msg['From'] = from_email
        msg['To'] = recipient_email
        
        # Generate group join link
        group_join_link = f"{app_url}/groups/{group_id}"
        
        # Create plain text email
        text_content = f"""
Hello {recipient_name},

You have been invited by {inviter_name} ({inviter_role}) to join the "{group_name}" channel in {settings.get('app_title', 'Simple Chat')}.

{f"Message from {inviter_name}: {custom_message}" if custom_message else ""}

To access this channel, please visit:
{group_join_link}

Thank you,
{settings.get('app_title', 'Innov8 GPT')} Team
"""
        
        # Create HTML version of the email
        html_content = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #0d6efd; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; }}
        .content {{ padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px; }}
        .button {{ display: inline-block; background-color: #0d6efd; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 10px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Channel Invitation</h2>
        </div>
        <div class="content">
            <p>Hello {recipient_name},</p>
            <p>You have been invited by <strong>{inviter_name}</strong> ({inviter_role}) to join the <strong>"{group_name}"</strong> channel in {settings.get('app_title', 'Simple Chat')}.</p>
            
            {f"<p><em>Message from {inviter_name}:</em> {custom_message}</p>" if custom_message else ""}
            
            <p>To access this channel, please click the button below:</p>
            <a href="{group_join_link}" class="button">Join Channel</a>
            
            <p class="footer">Thank you,<br>{settings.get('app_title', 'Innov8 GPT')} Team</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"Invitation email sent to {recipient_email} for group {group_name}")
        return True
        
    except Exception as e:
        print(f"Error sending invitation email: {str(e)}")
        return False