import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

load_dotenv()

class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Client = create_client(self.url, self.key)
        self.admin_client: Client = create_client(self.url, self.service_key)
    
    # User Management
    def create_user(self, email: str, password: str, username: str, **kwargs) -> Dict[str, Any]:
        """Create a new user in Supabase auth and users table"""
        try:
            # Create auth user
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if auth_response.user:
                # Create user in users table
                user_data = {
                    "id": auth_response.user.id,
                    "username": username,
                    "email": email,
                    "first_name": kwargs.get('first_name', ''),
                    "last_name": kwargs.get('last_name', ''),
                    "date_joined": datetime.now().isoformat()
                }
                
                user_response = self.client.table('users').insert(user_data).execute()
                
                # Create student profile
                profile_data = {
                    "user_id": auth_response.user.id,
                    "skills_offered": kwargs.get('skills_offered', ''),
                    "skills_wanted": kwargs.get('skills_wanted', '')
                }
                self.client.table('student_profiles').insert(profile_data).execute()
                
                return user_response.data[0] if user_response.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        response = self.client.table('users').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        response = self.client.table('users').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            response = self.client.table('users').update(updates).eq('id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    # Profile Management
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get student profile with user data"""
        response = self.client.table('student_profiles').select('*, users(*)').eq('user_id', user_id).execute()
        return response.data[0] if response.data else None
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update student profile"""
        try:
            response = self.client.table('student_profiles').update(updates).eq('user_id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    # Skill Management
    def create_skill(self, skill_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new skill"""
        try:
            response = self.client.table('skills').insert(skill_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating skill: {e}")
            return None
    
    def get_skills(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get skills with optional filters"""
        query = self.client.table('skills').select('*, users(username, first_name, last_name)')
        
        if filters:
            for key, value in filters.items():
                if value:
                    query = query.eq(key, value)
        
        response = query.limit(limit).execute()
        return response.data
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get skill by ID"""
        response = self.client.table('skills').select('*, users(*)').eq('id', skill_id).execute()
        return response.data[0] if response.data else None
    
    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> bool:
        """Update skill"""
        try:
            response = self.client.table('skills').update(updates).eq('id', skill_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating skill: {e}")
            return False
    
    def delete_skill(self, skill_id: str) -> bool:
        """Delete skill"""
        try:
            response = self.client.table('skills').delete().eq('id', skill_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting skill: {e}")
            return False
    
    # Skill Request Management
    def create_skill_request(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a skill request"""
        try:
            response = self.client.table('skill_requests').insert(request_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating skill request: {e}")
            return None
    
    def get_user_skill_requests(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get requests made and received by user"""
        made_response = self.client.table('skill_requests').select('*, skills(*, users(*))').eq('requester_id', user_id).execute()
        received_response = self.client.table('skill_requests').select('*, skills(*, users(*))').eq('owner_id', user_id).execute()
        
        return {
            'made': made_response.data,
            'received': received_response.data
        }
    
    def update_skill_request_status(self, request_id: str, status: str) -> bool:
        """Update skill request status"""
        updates = {'status': status}
        if status == 'IN_PROGRESS':
            updates['started_at'] = datetime.now().isoformat()
        elif status == 'COMPLETED':
            updates['completed_at'] = datetime.now().isoformat()
        
        try:
            response = self.client.table('skill_requests').update(updates).eq('id', request_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating request status: {e}")
            return False
    
    # Message Management
    def send_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message"""
        try:
            response = self.client.table('messages').insert(message_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def get_conversation(self, user1_id: str, user2_id: str) -> List[Dict[str, Any]]:
        """Get messages between two users"""
        response = self.client.table('messages').select('*').or_(f'from_user_id.eq.{user1_id},to_user_id.eq.{user1_id}').or_(f'from_user_id.eq.{user2_id},to_user_id.eq.{user2_id}').order('sent_at').execute()
        return response.data
    
    def get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        # This is a simplified version - you might want to optimize this
        response = self.client.table('messages').select('*').or_(f'from_user_id.eq.{user_id},to_user_id.eq.{user_id}').order('sent_at', desc=True).execute()
        return response.data
    
    # Review Management
    def create_review(self, review_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a review"""
        try:
            response = self.client.table('reviews').insert(review_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating review: {e}")
            return None
    
    def get_skill_reviews(self, skill_id: str) -> List[Dict[str, Any]]:
        """Get reviews for a skill"""
        response = self.client.table('reviews').select('*, users(username, first_name, last_name)').eq('skill_id', skill_id).order('created_at', desc=True).execute()
        return response.data
    
    # Meeting Management
    def create_meeting(self, meeting_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a meeting"""
        try:
            response = self.client.table('meetings').insert(meeting_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating meeting: {e}")
            return None
    
    def add_meeting_participants(self, meeting_id: str, user_ids: List[str]) -> bool:
        """Add participants to a meeting"""
        try:
            participants_data = [{'meeting_id': meeting_id, 'user_id': user_id} for user_id in user_ids]
            response = self.client.table('meeting_participants').insert(participants_data).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error adding meeting participants: {e}")
            return False
    
    def get_user_meetings(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get user's meetings (organized and participating)"""
        organized = self.client.table('meetings').select('*').eq('organizer_id', user_id).execute()
        
        participating = self.client.table('meeting_participants').select('meetings(*)').eq('user_id', user_id).execute()
        participating_meetings = [item['meetings'] for item in participating.data if item.get('meetings')]
        
        return {
            'organized': organized.data,
            'participating': participating_meetings
        }
    
    # Notification Management
    def create_notification(self, notification_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a notification"""
        try:
            response = self.client.table('notifications').insert(notification_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user notifications"""
        query = self.client.table('notifications').select('*').eq('user_id', user_id)
        
        if unread_only:
            query = query.eq('is_read', False)
        
        response = query.order('created_at', desc=True).execute()
        return response.data
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            response = self.client.table('notifications').update({'is_read': True}).eq('id', notification_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error marking notification read: {e}")
            return False
    
    # Admin Functions
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin only)"""
        response = self.admin_client.table('users').select('*').execute()
        return response.data
    
    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all skills (admin only)"""
        response = self.admin_client.table('skills').select('*, users(*)').execute()
        return response.data
    
    def get_all_skill_requests(self) -> List[Dict[str, Any]]:
        """Get all skill requests (admin only)"""
        response = self.admin_client.table('skill_requests').select('*, skills(*), users!skill_requests_requester_id_fkey(username), users!skill_requests_owner_id_fkey(username)').execute()
        return response.data
    
    def delete_user_admin(self, user_id: str) -> bool:
        """Delete user (admin only)"""
        try:
            # Delete from auth (this would typically be done via Supabase admin API)
            response = self.admin_client.table('users').delete().eq('id', user_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

# Global instance
supabase_service = SupabaseService()