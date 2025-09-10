"""
Test cases for NPCL Prompts and Customer Service Workflow.
Tests NPCL-specific business logic and conversation flow.
"""

import pytest
from unittest.mock import patch
import random

from src.voice_assistant.ai.npcl_prompts import (
    NPCLCustomerService, NPCLComplaint, NPCLServiceType, npcl_customer_service
)


class TestNPCLComplaint:
    """Test cases for NPCLComplaint dataclass"""
    
    def test_initialization(self):
        """Test complaint initialization"""
        complaint = NPCLComplaint(
            complaint_id="000054321",
            customer_name="dheeraj",
            area="Sector 62, Noida",
            issue_type="Power outage",
            status="In Progress"
        )
        
        assert complaint.complaint_id == "000054321"
        assert complaint.customer_name == "dheeraj"
        assert complaint.area == "Sector 62, Noida"
        assert complaint.issue_type == "Power outage"
        assert complaint.status == "In Progress"
        assert complaint.priority == "normal"  # Default value
        assert complaint.estimated_resolution == "24 hours"  # Default value
    
    def test_initialization_with_custom_values(self):
        """Test complaint initialization with custom priority and resolution"""
        complaint = NPCLComplaint(
            complaint_id="000054322",
            customer_name="nidhi",
            area="Greater Noida",
            issue_type="Voltage fluctuation",
            status="Assigned",
            priority="high",
            estimated_resolution="12 hours"
        )
        
        assert complaint.priority == "high"
        assert complaint.estimated_resolution == "12 hours"


class TestNPCLCustomerService:
    """Test cases for NPCLCustomerService"""
    
    def setup_method(self):
        """Setup for each test"""
        self.service = NPCLCustomerService()
    
    def test_initialization(self):
        """Test customer service initialization"""
        assert len(self.service.sample_names) > 0
        assert "dheeraj" in self.service.sample_names
        assert "nidhi" in self.service.sample_names
        assert "nikunj" in self.service.sample_names
        
        assert len(self.service.complaints_db) > 0
        assert "000054321" in self.service.complaints_db
        
        assert len(self.service.service_areas) > 0
        assert "Noida" in self.service.service_areas
        assert "Greater Noida" in self.service.service_areas
    
    def test_get_system_instruction(self):
        """Test system instruction generation"""
        instruction = self.service.get_system_instruction()
        
        assert isinstance(instruction, str)
        assert len(instruction) > 0
        
        # Check key elements
        assert "NPCL" in instruction
        assert "Welcome to NPCL" in instruction
        assert "dheeraj" in instruction
        assert "nidhi" in instruction
        assert "nikunj" in instruction
        assert "zero zero zero zero five four three two one zero" in instruction
        assert "Sir/Madam" in instruction
    
    def test_get_welcome_message(self):
        """Test welcome message"""
        message = self.service.get_welcome_message()
        
        assert message == "Welcome to NPCL! I am checking your information."
    
    def test_get_name_verification_prompt(self):
        """Test name verification prompt generation"""
        # Test multiple times to check randomness
        prompts = set()
        for _ in range(10):
            prompt = self.service.get_name_verification_prompt()
            prompts.add(prompt)
            
            assert "Is this connection registered with" in prompt
            # Extract name from prompt
            name = prompt.split("with ")[1].rstrip("?")
            assert name in self.service.sample_names
        
        # Should have some variation (not always the same name)
        assert len(prompts) > 1
    
    def test_process_user_response_affirmative(self):
        """Test processing affirmative user responses"""
        affirmative_responses = ["yes", "haan", "ok", "correct", "right", "ji"]
        
        for response in affirmative_responses:
            result = self.service.process_user_response(response)
            
            assert result["action"] == "complaint_status"
            assert result["complaint_id"] == "000054321"
            assert result["next_step"] == "await_further_inquiry"
            assert "Thanks for confirming" in result["message"]
            # The message should contain the complaint number in some format
            assert "complaint" in result["message"].lower()
            assert "000054321" in result["message"] or "0 0 0 0 5 4 3 2 1" in result["message"]
    
    def test_process_user_response_negative(self):
        """Test processing negative user responses"""
        negative_responses = ["no", "nahi", "wrong", "nope", "incorrect"]
        
        for response in negative_responses:
            result = self.service.process_user_response(response)
            
            assert result["action"] == "name_correction"
            assert result["next_step"] == "await_name_or_complaint"
            assert "No problem at all!" in result["message"]
            assert "correct name or your complaint number" in result["message"]
    
    def test_process_user_response_complaint_number(self):
        """Test processing complaint number input"""
        complaint_numbers = ["000054321", "000-054-321", "000 054 321"]
        
        for complaint_num in complaint_numbers:
            result = self.service.process_user_response(complaint_num)
            
            assert result["action"] == "complaint_status"
            assert result["complaint_id"] == "000054321"  # Normalized
            assert result["next_step"] == "await_further_inquiry"
            assert "Thank you! Complaint" in result["message"]
            # The message should contain the complaint number in some format
            assert "complaint" in result["message"].lower()
            assert "000054321" in result["message"] or "0 0 0 0 5 4 3 2 1" in result["message"]
    
    def test_process_user_response_customer_name(self):
        """Test processing customer name input"""
        for name in self.service.sample_names:
            result = self.service.process_user_response(f"My name is {name}")
            
            assert result["action"] == "name_accepted"
            assert result["customer_name"] == name.title()
            assert result["next_step"] == "await_service_request"
            assert f"Thank you {name.title()}" in result["message"]
            assert "sir/madam" in result["message"]
    
    def test_process_user_response_service_requests(self):
        """Test processing service request inputs"""
        # Power-related requests
        power_requests = ["power outage", "no electricity", "light problem", "outage in my area"]
        
        for request in power_requests:
            result = self.service.process_user_response(request)
            
            assert result["action"] == "power_complaint"
            assert result["next_step"] == "collect_area_info"
            assert "power supply issue" in result["message"]
            assert "register a complaint" in result["message"]
        
        # Billing-related requests
        billing_requests = ["bill problem", "billing issue", "payment query", "amount due"]
        
        for request in billing_requests:
            result = self.service.process_user_response(request)
            
            assert result["action"] == "billing_inquiry"
            assert result["next_step"] == "collect_consumer_info"
            assert "For billing inquiries, I can help you" in result["message"]
            assert "consumer number" in result["message"]
    
    def test_process_user_response_unclear_input(self):
        """Test processing unclear input"""
        unclear_inputs = ["hello", "what?", "xyz", "random text"]
        
        for unclear_input in unclear_inputs:
            result = self.service.process_user_response(unclear_input)
            
            assert result["action"] == "clarification_needed"
            assert result["next_step"] == "await_clear_input"
            assert "didn't quite understand" in result["message"]
    
    def test_is_complaint_number(self):
        """Test complaint number pattern detection"""
        # Valid complaint numbers
        valid_numbers = ["000054321", "000-054-321", "000 054 321", "123456789"]
        
        for number in valid_numbers:
            assert self.service._is_complaint_number(number) == True
        
        # Invalid patterns
        invalid_numbers = ["12345", "abcd", "000-54-321-extra", ""]
        
        for number in invalid_numbers:
            assert self.service._is_complaint_number(number) == False
    
    def test_extract_complaint_number(self):
        """Test complaint number extraction"""
        test_cases = [
            ("000054321", "000054321"),
            ("000-054-321", "000054321"),
            ("000 054 321", "000054321"),
            ("My complaint number is 000054321", "000054321"),
            ("Call 123456789 for help", "123456789"),
            ("No number here", "000054321")  # Default
        ]
        
        for input_text, expected in test_cases:
            result = self.service._extract_complaint_number(input_text)
            assert result == expected
    
    def test_extract_customer_name(self):
        """Test customer name extraction"""
        for name in self.service.sample_names:
            test_inputs = [
                f"My name is {name}",
                f"I am {name}",
                f"{name} speaking",
                name
            ]
            
            for input_text in test_inputs:
                result = self.service._extract_customer_name(input_text.lower())
                assert result == name.title()
        
        # Test unknown name
        result = self.service._extract_customer_name("unknown person")
        assert result == "Customer"
    
    def test_register_new_complaint(self):
        """Test new complaint registration"""
        initial_count = len(self.service.complaints_db)
        
        complaint_id = self.service.register_new_complaint(
            customer_name="test_customer",
            area="Test Area",
            issue_type="Test Issue"
        )
        
        # Check complaint was registered
        assert len(self.service.complaints_db) == initial_count + 1
        assert complaint_id in self.service.complaints_db
        
        # Check complaint details
        complaint = self.service.complaints_db[complaint_id]
        assert complaint.customer_name == "test_customer"
        assert complaint.area == "Test Area"
        assert complaint.issue_type == "Test Issue"
        assert complaint.status == "Registered"
        assert complaint.priority == "normal"
    
    def test_get_complaint_status(self):
        """Test complaint status retrieval"""
        # Existing complaint
        complaint = self.service.get_complaint_status("000054321")
        assert complaint is not None
        assert complaint.complaint_id == "000054321"
        assert complaint.customer_name == "dheeraj"
        
        # Non-existent complaint
        complaint = self.service.get_complaint_status("999999999")
        assert complaint is None
    
    def test_get_service_areas(self):
        """Test service areas retrieval"""
        areas = self.service.get_service_areas()
        
        assert isinstance(areas, list)
        assert len(areas) > 0
        assert "Noida" in areas
        assert "Greater Noida" in areas
        assert "Sector 62" in areas
    
    def test_is_service_area(self):
        """Test service area validation"""
        # Valid service areas
        valid_areas = ["Noida", "Greater Noida", "Sector 62", "sector 18", "ALPHA"]
        
        for area in valid_areas:
            assert self.service.is_service_area(area) == True
        
        # Invalid areas
        invalid_areas = ["Mumbai", "Delhi", "Unknown Area"]
        
        for area in invalid_areas:
            assert self.service.is_service_area(area) == False
    
    def test_complaints_database_structure(self):
        """Test complaints database structure"""
        for complaint_id, complaint in self.service.complaints_db.items():
            assert isinstance(complaint, NPCLComplaint)
            assert complaint.complaint_id == complaint_id
            assert len(complaint_id) == 9  # NPCL complaint ID format
            assert complaint_id.startswith("00005")
            
            # Check required fields
            assert complaint.customer_name
            assert complaint.area
            assert complaint.issue_type
            assert complaint.status
            assert complaint.priority in ["low", "normal", "medium", "high"]


class TestNPCLServiceType:
    """Test cases for NPCLServiceType enum"""
    
    def test_service_types(self):
        """Test service type enumeration"""
        expected_types = [
            "power_supply", "billing", "complaint", 
            "new_connection", "disconnection", "general_inquiry"
        ]
        
        for service_type in expected_types:
            assert hasattr(NPCLServiceType, service_type.upper())
            assert getattr(NPCLServiceType, service_type.upper()).value == service_type


class TestGlobalNPCLService:
    """Test cases for global NPCL service instance"""
    
    def test_global_instance(self):
        """Test global NPCL customer service instance"""
        assert npcl_customer_service is not None
        assert isinstance(npcl_customer_service, NPCLCustomerService)
    
    def test_global_instance_functionality(self):
        """Test global instance functionality"""
        # Test basic functionality
        instruction = npcl_customer_service.get_system_instruction()
        assert "NPCL" in instruction
        
        welcome = npcl_customer_service.get_welcome_message()
        assert "Welcome to NPCL" in welcome
        
        # Test response processing
        result = npcl_customer_service.process_user_response("yes")
        assert result["action"] == "complaint_status"


@pytest.mark.integration
class TestNPCLCustomerServiceIntegration:
    """Integration tests for NPCL customer service"""
    
    def test_complete_conversation_flow_affirmative(self):
        """Test complete conversation flow with affirmative response"""
        service = NPCLCustomerService()
        
        # Step 1: Get welcome message
        welcome = service.get_welcome_message()
        assert "Welcome to NPCL" in welcome
        
        # Step 2: Get name verification prompt
        name_prompt = service.get_name_verification_prompt()
        assert "Is this connection registered with" in name_prompt
        
        # Step 3: Process affirmative response
        result = service.process_user_response("yes")
        assert result["action"] == "complaint_status"
        assert "complaint zero zero zero zero five four three two one zero" in result["message"]
    
    def test_complete_conversation_flow_negative(self):
        """Test complete conversation flow with negative response"""
        service = NPCLCustomerService()
        
        # Step 1: Welcome and name verification
        welcome = service.get_welcome_message()
        name_prompt = service.get_name_verification_prompt()
        
        # Step 2: Process negative response
        result = service.process_user_response("no")
        assert result["action"] == "name_correction"
        
        # Step 3: Provide correct name
        result = service.process_user_response("My name is dheeraj")
        assert result["action"] == "name_accepted"
        assert result["customer_name"] == "Dheeraj"
    
    def test_complaint_number_workflow(self):
        """Test complaint number workflow"""
        service = NPCLCustomerService()
        
        # Process complaint number
        result = service.process_user_response("000054321")
        assert result["action"] == "complaint_status"
        assert result["complaint_id"] == "000054321"
        
        # Verify complaint exists
        complaint = service.get_complaint_status("000054321")
        assert complaint is not None
        assert complaint.customer_name == "dheeraj"
    
    def test_service_request_workflow(self):
        """Test service request workflow"""
        service = NPCLCustomerService()
        
        # Power outage request
        result = service.process_user_response("There is a power outage in my area")
        assert result["action"] == "power_complaint"
        assert "register a complaint" in result["message"]
        
        # Billing inquiry
        result = service.process_user_response("I have a billing question")
        assert result["action"] == "billing_inquiry"
        assert "consumer number" in result["message"]
    
    def test_new_complaint_registration_workflow(self):
        """Test new complaint registration workflow"""
        service = NPCLCustomerService()
        
        # Register new complaint
        complaint_id = service.register_new_complaint(
            customer_name="test_user",
            area="Sector 99, Noida",
            issue_type="Street light not working"
        )
        
        # Verify complaint was registered
        assert complaint_id.startswith("00005")
        assert len(complaint_id) == 9
        
        # Retrieve and verify complaint
        complaint = service.get_complaint_status(complaint_id)
        assert complaint is not None
        assert complaint.customer_name == "test_user"
        assert complaint.area == "Sector 99, Noida"
        assert complaint.issue_type == "Street light not working"
        assert complaint.status == "Registered"


if __name__ == "__main__":
    pytest.main([__file__])