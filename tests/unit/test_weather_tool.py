"""
Test cases for Weather Tool.
Tests weather data retrieval and NPCL-specific functionality.
"""

import pytest
from unittest.mock import patch

from src.voice_assistant.tools.weather_tool import WeatherTool, weather_tool
from src.voice_assistant.ai.function_calling import FunctionDefinition


class TestWeatherTool:
    """Test cases for WeatherTool"""
    
    def setup_method(self):
        """Setup for each test"""
        self.tool = WeatherTool()
    
    def test_initialization(self):
        """Test weather tool initialization"""
        assert len(self.tool.weather_cities) > 0
        assert "Delhi" in self.tool.weather_cities
        assert "Mumbai" in self.tool.weather_cities
        assert "Noida" in self.tool.weather_cities  # NPCL specific
        assert "Greater Noida" in self.tool.weather_cities  # NPCL specific
    
    def test_get_definition(self):
        """Test function definition"""
        definition = self.tool.get_definition()
        
        assert isinstance(definition, FunctionDefinition)
        assert definition.name == "get_weather"
        assert "weather information" in definition.description.lower()
        assert "npcl" in definition.description.lower()
        assert len(definition.parameters) == 1
        
        # Check parameter
        param = definition.parameters[0]
        assert param.name == "location"
        assert param.type == "string"
        assert param.required == True
    
    @pytest.mark.asyncio
    async def test_execute_known_city(self):
        """Test weather lookup for known city"""
        result = await self.tool.execute(location="Delhi")
        
        assert "result" in result
        weather_text = result["result"]
        
        # Check response contains expected elements
        assert "Delhi" in weather_text
        assert "°C" in weather_text
        assert "humidity" in weather_text.lower()
    
    @pytest.mark.asyncio
    async def test_execute_npcl_service_area(self):
        """Test weather lookup for NPCL service area"""
        result = await self.tool.execute(location="Noida")
        
        assert "result" in result
        weather_text = result["result"]
        
        # Check NPCL-specific response
        assert "Noida" in weather_text
        assert "NPCL service area" in weather_text
        assert "power supply should be stable" in weather_text
    
    @pytest.mark.asyncio
    async def test_execute_unknown_city(self):
        """Test weather lookup for unknown city"""
        result = await self.tool.execute(location="UnknownCity")
        
        assert "result" in result
        weather_text = result["result"]
        
        # Should still provide weather (default values)
        assert "UnknownCity" in weather_text
        assert "°C" in weather_text
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """Test weather lookup with simulated error"""
        with patch.object(self.tool, '_get_weather_data', side_effect=Exception("Test error")):
            result = await self.tool.execute(location="Delhi")
            
            assert "result" in result
            weather_text = result["result"]
            
            # Should return error message
            assert "Sorry" in weather_text
            assert "couldn't get weather" in weather_text
    
    def test_normalize_location(self):
        """Test location name normalization"""
        # Test basic normalization
        assert self.tool._normalize_location("delhi") == "Delhi"
        assert self.tool._normalize_location("MUMBAI") == "Mumbai"
        assert self.tool._normalize_location("  bangalore  ") == "Bangalore"
        
        # Test common variations
        assert self.tool._normalize_location("New Delhi") == "Delhi"
        assert self.tool._normalize_location("Bombay") == "Mumbai"
        assert self.tool._normalize_location("Calcutta") == "Kolkata"
        assert self.tool._normalize_location("Bengaluru") == "Bangalore"
        assert self.tool._normalize_location("Madras") == "Chennai"
        assert self.tool._normalize_location("Gurgaon") == "Gurugram"
    
    def test_get_weather_data_known_city(self):
        """Test weather data retrieval for known city"""
        temperature, condition, humidity, description = self.tool._get_weather_data("Delhi")
        
        assert "°C" in temperature
        assert isinstance(condition, str)
        assert "%" in humidity
        assert isinstance(description, str)
    
    def test_get_weather_data_unknown_city(self):
        """Test weather data retrieval for unknown city"""
        temperature, condition, humidity, description = self.tool._get_weather_data("UnknownCity")
        
        # Should return default values
        assert temperature == "25°C"
        assert condition == "Pleasant"
        assert humidity == "65%"
        assert description == "Moderate conditions"
    
    def test_format_weather_response_npcl_area(self):
        """Test weather response formatting for NPCL service area"""
        weather_data = ("28°C", "Sunny", "60%", "Clear skies")
        
        response = self.tool._format_weather_response("Noida", weather_data)
        
        assert "Noida" in response
        assert "28°C" in response
        assert "sunny" in response.lower()
        assert "60%" in response
        assert "NPCL service area" in response
        assert "power supply should be stable" in response
    
    def test_format_weather_response_general_city(self):
        """Test weather response formatting for general city"""
        weather_data = ("32°C", "Cloudy", "75%", "Overcast conditions")
        
        response = self.tool._format_weather_response("Mumbai", weather_data)
        
        assert "Mumbai" in response
        assert "32°C" in response
        assert "cloudy" in response.lower()
        assert "75%" in response
        assert "NPCL service area" not in response  # Should not mention NPCL
    
    def test_add_city_weather(self):
        """Test adding new city weather data"""
        initial_count = len(self.tool.weather_cities)
        
        self.tool.add_city_weather(
            city="TestCity",
            temperature="20°C",
            condition="Rainy",
            humidity="80%",
            description="Heavy rainfall"
        )
        
        # Check city was added
        assert len(self.tool.weather_cities) == initial_count + 1
        assert "TestCity" in self.tool.weather_cities
        
        # Check data
        weather_data = self.tool._get_weather_data("TestCity")
        assert weather_data[0] == "20°C"
        assert weather_data[1] == "Rainy"
        assert weather_data[2] == "80%"
        assert weather_data[3] == "Heavy rainfall"
    
    def test_get_supported_cities(self):
        """Test getting list of supported cities"""
        cities = self.tool.get_supported_cities()
        
        assert isinstance(cities, list)
        assert len(cities) > 0
        assert "Delhi" in cities
        assert "Mumbai" in cities
        assert "Noida" in cities
    
    def test_is_city_supported(self):
        """Test checking if city is supported"""
        # Known cities
        assert self.tool.is_city_supported("Delhi") == True
        assert self.tool.is_city_supported("delhi") == True  # Case insensitive
        assert self.tool.is_city_supported("New Delhi") == True  # Variation
        
        # Unknown city
        assert self.tool.is_city_supported("UnknownCity") == False
    
    def test_npcl_specific_cities(self):
        """Test NPCL-specific cities are included"""
        npcl_cities = ["Noida", "Greater Noida", "Ghaziabad", "Faridabad", "Gurugram"]
        
        for city in npcl_cities:
            assert city in self.tool.weather_cities
            assert self.tool.is_city_supported(city) == True
    
    def test_weather_data_structure(self):
        """Test weather data structure consistency"""
        for city, data in self.tool.weather_cities.items():
            assert len(data) == 4  # temperature, condition, humidity, description
            
            temperature, condition, humidity, description = data
            
            # Check temperature format
            assert "°C" in temperature
            
            # Check humidity format
            assert "%" in humidity
            
            # Check all are strings
            assert isinstance(temperature, str)
            assert isinstance(condition, str)
            assert isinstance(humidity, str)
            assert isinstance(description, str)
    
    @pytest.mark.asyncio
    async def test_integration_with_function_calling(self):
        """Test integration with function calling system"""
        # Test that the tool can be used as a function
        definition = self.tool.get_definition()
        gemini_format = definition.to_gemini_format()
        
        # Check Gemini format is valid
        assert "name" in gemini_format
        assert "description" in gemini_format
        assert "parameters" in gemini_format
        assert gemini_format["name"] == "get_weather"
        
        # Test parameter validation
        validated_params = self.tool.validate_parameters({"location": "Delhi"})
        assert validated_params["location"] == "Delhi"
        
        # Test execution
        result = await self.tool.execute(**validated_params)
        assert "result" in result
        assert "Delhi" in result["result"]


class TestGlobalWeatherTool:
    """Test cases for global weather tool instance"""
    
    def test_global_instance(self):
        """Test global weather tool instance"""
        assert weather_tool is not None
        assert isinstance(weather_tool, WeatherTool)
    
    @pytest.mark.asyncio
    async def test_global_instance_functionality(self):
        """Test global instance functionality"""
        result = await weather_tool.execute(location="Mumbai")
        
        assert "result" in result
        assert "Mumbai" in result["result"]


@pytest.mark.integration
class TestWeatherToolIntegration:
    """Integration tests for weather tool"""
    
    @pytest.mark.asyncio
    async def test_full_weather_workflow(self):
        """Test complete weather lookup workflow"""
        tool = WeatherTool()
        
        # Test multiple cities
        cities_to_test = ["Delhi", "Mumbai", "Noida", "UnknownCity"]
        
        for city in cities_to_test:
            result = await tool.execute(location=city)
            
            assert "result" in result
            weather_text = result["result"]
            
            # Check basic response structure
            assert city in weather_text
            assert "°C" in weather_text
            
            # Check NPCL-specific response for service areas
            if city in ["Noida", "Greater Noida", "Ghaziabad", "Faridabad", "Gurugram"]:
                assert "NPCL service area" in weather_text
            else:
                assert "NPCL service area" not in weather_text
    
    def test_weather_data_completeness(self):
        """Test that all major Indian cities have weather data"""
        tool = WeatherTool()
        
        major_cities = [
            "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata",
            "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow"
        ]
        
        for city in major_cities:
            assert tool.is_city_supported(city), f"Major city {city} not supported"
            
            # Test weather data retrieval
            weather_data = tool._get_weather_data(city)
            assert len(weather_data) == 4
            assert "°C" in weather_data[0]  # Temperature
            assert "%" in weather_data[2]   # Humidity


if __name__ == "__main__":
    pytest.main([__file__])