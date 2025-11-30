"""
Simple email utility for sending emails via SMTP.
The EmailService class only handles sending - create your email content in the calling code.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from app.config import email_settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Simple email sender - just handles SMTP connection and sending.
    Create your email content (subject, body, HTML) in your calling code.
    
    Usage:
        email_service = EmailService()
        email_service.send(
            to_email="user@example.com",
            subject="Your OTP Code",
            plain_text="Your OTP is: 123456",
            html_content="<h1>Your OTP is: 123456</h1>"
        )
    """
    
    def __init__(self):
        self.smtp_host = email_settings.SMTP_HOST
        self.smtp_port = email_settings.SMTP_PORT
        self.smtp_username = email_settings.SMTP_USERNAME
        self.smtp_password = email_settings.SMTP_PASSWORD
        self.from_email = email_settings.SMTP_FROM_EMAIL
        self.from_name = email_settings.SMTP_FROM_NAME
    
    def send(
        self,
        to_email: str,
        subject: str,
        plain_text: Optional[str] = None,
        html_content: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            plain_text: Plain text email body (optional)
            html_content: HTML email body (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        
        Note:
            At least one of plain_text or html_content must be provided.
        """
        if not plain_text and not html_content:
            logger.error("Either plain_text or html_content must be provided")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Attach plain text if provided
            if plain_text:
                part1 = MIMEText(plain_text, "plain")
                message.attach(part1)
            
            # Attach HTML if provided
            if html_content:
                part2 = MIMEText(html_content, "html")
                message.attach(part2)
            
            # Send email via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False


# Singleton instance for easy import
email_service = EmailService()
