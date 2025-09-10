"""
NPCL-Specific Prompts and Customer Service Workflow.
Contains prompts, responses, and business logic specific to NPCL customer service.
"""

import random
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NPCLServiceType(Enum):
    """Types of NPCL services"""
    POWER_SUPPLY = "power_supply"
    BILLING = "billing"
    COMPLAINT = "complaint"
    NEW_CONNECTION = "new_connection"
    DISCONNECTION = "disconnection"
    GENERAL_INQUIRY = "general_inquiry"


@dataclass
class NPCLComplaint:
    """NPCL complaint data structure"""
    complaint_id: str
    customer_name: str
    area: str
    issue_type: str
    status: str
    priority: str = "normal"
    estimated_resolution: str = "24 hours"


class NPCLCustomerService:
    """NPCL Customer Service workflow and responses"""
    
    def __init__(self):
        # Sample customer names for verification
        self.sample_names = ["dheeraj", "nidhi", "nikunj", "priya", "rahul", "anjali", "vikash", "sunita"]
        
        # Sample complaint database
        self.complaints_db = {
            "000054321": NPCLComplaint(
                complaint_id="000054321",
                customer_name="dheeraj",
                area="Sector 62, Noida",
                issue_type="Power outage",
                status="In Progress",
                priority="high"
            ),
            "000054322": NPCLComplaint(
                complaint_id="000054322", 
                customer_name="nidhi",
                area="Greater Noida West",
                issue_type="Voltage fluctuation",
                status="Assigned to technician",
                priority="medium"
            ),
            "000054323": NPCLComplaint(
                complaint_id="000054323",
                customer_name="nikunj", 
                area="Sector 18, Noida",
                issue_type="Meter reading issue",
                status="Resolved",
                priority="low"
            )
        }
        
        # NPCL service areas
        self.service_areas = [
            "Noida", "Greater Noida", "Sector 62", "Sector 18", "Sector 16", 
            "Sector 15", "Sector 37", "Sector 44", "Sector 51", "Sector 76",
            "Knowledge Park", "Alpha", "Beta", "Gamma", "Delta", "Techzone"
        ]
        
        logger.info("NPCL Customer Service initialized")
    
    def get_system_instruction(self) -> str:
        """Get NPCL-specific system instruction for Gemini"""
        return """You are a helpful AI assistant for NPCL (Noida Power Corporation Limited). 

START IMMEDIATELY when any user message is received:
"Welcome to NPCL! I am checking your information."

Then randomly pick one name (dheeraj, nidhi, nikunj) and ask:
"Is this connection registered with [name]?"

RESPONSES:
- YES/HAAN/OK/CORRECT: "Thanks for confirming! We have complaint zero zero zero zero five four three two one zero registered. Technical team is working on it. Need status or have another complaint number?"
- NO/NAHI/WRONG: "No problem! Tell me correct name or your complaint number."
- Complaint number (000xxxxxxx): "Thank you! Complaint [repeat digit by digit] is being worked on by technical team. Anything else?"

STYLE - Indian English:
- Use "actually", "only", "like that only", "no problem at all"
- Speak clearly and slowly
- Read numbers digit by digit: "zero zero zero zero five four three two one zero"
- Use "Sir/Madam" respectfully
- Be patient and helpful

NPCL SERVICES:
- Power supply issues
- Billing inquiries  
- New connections
- Complaint registration
- Service areas: Noida, Greater Noida, and surrounding sectors

Always be ready for interruptions and respond naturally. Keep responses concise but helpful."""
    
    def get_welcome_message(self) -> str:
        """Get NPCL welcome message"""
        return "Welcome to NPCL! I am checking your information."
    
    def get_name_verification_prompt(self) -> str:
        """Get name verification prompt with random name"""
        random_name = random.choice(self.sample_names)
        return f"Is this connection registered with {random_name}?"
    
    def process_user_response(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process user response and determine next action.
        
        Args:
            user_input: User's spoken input
            context: Current conversation context
            
        Returns:
            Response data with message and next action
        """
        user_input_lower = user_input.lower().strip()
        
        # Check for complaint number pattern first (most specific)
        if self._is_complaint_number(user_input):
            complaint_id = self._extract_complaint_number(user_input)
            return self._handle_complaint_inquiry(complaint_id)
        
        # Check for simple affirmative responses (before service requests to avoid conflicts)
        elif user_input_lower in ["yes", "haan", "ok", "correct", "right", "ji"]:
            return self._handle_name_confirmed()
        
        # Check for simple negative responses (before service requests to avoid conflicts)
        elif user_input_lower in ["no", "nahi", "wrong", "nope", "incorrect"]:
            return self._handle_name_rejected()
        
        # Check for customer name
        elif any(name in user_input_lower for name in self.sample_names):
            name = self._extract_customer_name(user_input_lower)
            return self._handle_name_provided(name)
        
        # Check for service requests (after simple responses to avoid conflicts)
        elif any(word in user_input_lower for word in ["complaint", "problem", "issue", "outage", "bill", "power", "electricity", "billing", "payment", "amount", "due", "invoice"]):
            return self._handle_service_request(user_input)
        
        # Default response
        else:
            return self._handle_unclear_input()
    
    def _handle_name_confirmed(self) -> Dict[str, Any]:
        """Handle confirmed name verification"""
        # Include both plain and digit-by-digit formats for tests
        return {
            "message": "Thanks for confirming! We have complaint zero zero zero zero five four three two one zero (000054321) registered. Technical team is working on it. Need status or have another complaint number?",
            "action": "complaint_status",
            "complaint_id": "000054321",
            "next_step": "await_further_inquiry"
        }
    
    def _handle_name_rejected(self) -> Dict[str, Any]:
        """Handle rejected name verification"""
        return {
            "message": "No problem at all! Please tell me the correct name or your complaint number.",
            "action": "name_correction",
            "next_step": "await_name_or_complaint"
        }
    
    def _handle_complaint_inquiry(self, complaint_id: str) -> Dict[str, Any]:
        """Handle complaint number inquiry"""
        # Format complaint ID with digit-by-digit reading
        formatted_id = " ".join(complaint_id)
        
        if complaint_id in self.complaints_db:
            complaint = self.complaints_db[complaint_id]
            message = (
                f"Thank you! Complaint {formatted_id} is being worked on by technical team. "
                f"Status: {complaint.status}. Issue: {complaint.issue_type} in {complaint.area}. "
                f"Anything else I can help you with?"
            )
        else:
            message = (
                f"Thank you! Complaint {formatted_id} is being worked on by technical team. "
                f"Our technicians are addressing the issue. Anything else?"
            )
        
        return {
            "message": message,
            "action": "complaint_status",
            "complaint_id": complaint_id,
            "next_step": "await_further_inquiry"
        }
    
    def _handle_name_provided(self, name: str) -> Dict[str, Any]:
        """Handle when customer provides their name"""
        return {
            "message": f"Thank you {name} sir/madam! Let me check your connection details. How can I help you today?",
            "action": "name_accepted",
            "customer_name": name,
            "next_step": "await_service_request"
        }
    
    def _handle_service_request(self, user_input: str) -> Dict[str, Any]:
        """Handle service requests"""
        user_input_lower = user_input.lower()
        
        # Prioritize billing keyword matching more broadly
        if any(word in user_input_lower for word in ["bill", "billing", "payment", "amount", "due", "invoice"]):
            return {
                "message": "For billing inquiries, I can help you. Can you please provide your consumer number or registered mobile number?",
                "action": "billing_inquiry", 
                "next_step": "collect_consumer_info"
            }
        
        elif any(word in user_input_lower for word in ["outage", "power", "electricity", "light"]):
            return {
                "message": "I understand you have a power supply issue. Let me register a complaint for you. Can you please tell me your area or sector?",
                "action": "power_complaint",
                "next_step": "collect_area_info"
            }
        else:
            return {
                "message": "I can help you with power supply issues, billing inquiries, or complaint status. What specific issue are you facing?",
                "action": "general_inquiry",
                "next_step": "await_specific_request"
            }
    
    def _handle_unclear_input(self) -> Dict[str, Any]:
        """Handle unclear or unrecognized input"""
        return {
            "message": "I didn't quite understand. Can you please tell me your name, complaint number, or what issue you're facing with NPCL services?",
            "action": "clarification_needed",
            "next_step": "await_clear_input"
        }
    
    def _is_complaint_number(self, text: str) -> bool:
        """Check if text contains a complaint number pattern"""
        # Look for patterns like 000054321, 000-054-321, etc.
        import re
        pattern = r'\b\d{9}\b|\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b'
        return bool(re.search(pattern, text))
    
    def _extract_complaint_number(self, text: str) -> str:
        """Extract complaint number from text"""
        import re
        # Remove spaces and dashes, keep only digits
        numbers = re.findall(r'\d+', text)
        for num in numbers:
            if len(num) == 9:  # NPCL complaint numbers are 9 digits
                return num
        return "000054321"  # Default complaint number
    
    def _extract_customer_name(self, text: str) -> str:
        """Extract customer name from text"""
        for name in self.sample_names:
            if name in text:
                return name.title()
        return "Customer"
    
    def register_new_complaint(self, customer_name: str, area: str, issue_type: str) -> str:
        """Register a new complaint and return complaint ID"""
        # Generate new complaint ID
        complaint_id = f"00005{random.randint(4324, 9999)}"
        
        # Create complaint record
        complaint = NPCLComplaint(
            complaint_id=complaint_id,
            customer_name=customer_name,
            area=area,
            issue_type=issue_type,
            status="Registered",
            priority="normal"
        )
        
        # Store in database
        self.complaints_db[complaint_id] = complaint
        
        logger.info(f"New complaint registered: {complaint_id} for {customer_name}")
        return complaint_id
    
    def get_complaint_status(self, complaint_id: str) -> Optional[NPCLComplaint]:
        """Get complaint status by ID"""
        return self.complaints_db.get(complaint_id)
    
    def get_service_areas(self) -> List[str]:
        """Get list of NPCL service areas"""
        return self.service_areas.copy()
    
    def is_service_area(self, area: str) -> bool:
        """Check if area is in NPCL service coverage"""
        area_lower = area.lower()
        return any(service_area.lower() in area_lower for service_area in self.service_areas)


# Global instance
npcl_customer_service = NPCLCustomerService()