# Travel Agent MCP Testing Guide

This guide provides test scenarios to manually validate your travel agent system. Test these scenarios to ensure all components work correctly.

## Setup Requirements

1. **Environment Variables:**
   ```bash
   export OPENAI_API_KEY="your-key-here"
   # OR
   export OPENROUTER_API_KEY="your-key-here"
   ```

2. **Start the System:**
   ```bash
   python mcp_cli.py start
   python travel_agent.py

   ```

## Basic Functionality Tests

### Simple Travel Planning ( Working Example)
```
Two weeks in November to South Korea from Portland
```
**Expected:** Should automatically:
- Get current date for context
- Search flights from PDX to ICN with specific dates
- Find hotels in Seoul with check-in/out dates
- Provide weather information for November
- Include cultural insights about South Korea and Seoul
- Offer next steps for booking and activities
- Handle follow-up questions about detailed activities

### Weekend Trip Planning
```
I want to plan a weekend trip to Paris from New York in December. Can you help me find flights and hotels?
```
**Expected:** Should search flights, hotels, get weather, and create basic itinerary.

### Multi-City Trip
```
Plan a 10-day trip: New York → London (3 days) → Paris (4 days) → Rome (3 days) → back to New York. Budget around $3000.
```
**Expected:** Should handle complex multi-city routing with budget considerations.

### Invalid Locations
```
Plan a trip to Atlantis and Narnia next month
```
**Expected:** Should handle non-existent locations gracefully and suggest alternatives.

### Impossible Dates
```
Book a flight for yesterday from Miami to Seattle
```
**Expected:** Should catch past dates and request valid future dates.

### Missing Information
```
Find me a hotel
```
**Expected:** Should ask for required details (location, dates, etc.).

### Conflicting Requirements
```
Find the cheapest luxury hotel in Manhattan for tonight under $50
```
**Expected:** Should identify conflicting requirements and clarify.

### Multi-Modal Transit
```
How can I get from downtown San Francisco to Napa Valley? Show me driving, public transit, and cycling options.
```
**Expected:** Should use multi_modal_route tool to compare all transportation modes.

### Complete Trip Planning
```
I'm a software engineer from San Francisco planning a 2-week European vacation in July. I love history, good food, and photography. Budget is $4000. I prefer trains over flights within Europe. Plan everything including flights, accommodations, and daily activities.
```
**Expected:** Should create comprehensive plan using multiple tools and preferences.

### Business Trip Planning
```
Plan a 3-day business trip to Chicago. I need to be there Tuesday-Thursday next week. Book flights, hotel near downtown, and suggest restaurants for client dinners.
```
**Expected:** Should handle business travel requirements with appropriate suggestions.

### Group Travel
```
Plan a bachelor party weekend in Las Vegas for 8 people. We need group accommodations, restaurant reservations, and activity suggestions.
```
**Expected:** Should handle group requirements and scale recommendations.

## Edge Cases

### Last-Minute Travel
```
I need to fly to London tonight for an emergency. What are my options?
```
**Expected:** Should find immediate travel options and handle urgency.

### Long-Term Planning
```
Plan a 6-month sabbatical trip around the world starting next year
```
**Expected:** Should handle long-term, complex planning with multiple destinations.

### Accessibility Requirements
```
Plan a trip to Barcelona for someone in a wheelchair. I need accessible hotels, transportation, and attractions.
```
**Expected:** Should consider accessibility in all recommendations.

### Multi-Generational Family Trip
```
Plan a 3-generation family trip to Japan for 7 people (ages 5, 12, 35, 38, 42, 68, 72). We need accessible accommodations, kid-friendly activities, and cultural experiences for grandparents. Budget $15,000 total.
```
**Expected:** Should handle group requirements and scale recommendations.

### Digital Nomad Route Planning
```
I'm a remote worker planning a 6-month digital nomad journey through Southeast Asia. I need reliable WiFi, coworking spaces, visa requirements, and budget accommodations under $50/night. Start in Bangkok.
```
**Expected:** Should handle long-term planning, specific requirements, visa research, budget constraints

### Adventure Sports & Safety
```
Plan an extreme sports trip to New Zealand: bungee jumping, skydiving, white-water rafting, and mountain climbing. Include safety certifications, insurance requirements, and emergency contacts.
```
**Expected:** Should handle specialized activity planning, safety considerations, risk assessment

### Sustainable & Eco-Tourism
```
Plan a carbon-neutral trip to Costa Rica focusing on eco-lodges, wildlife conservation, and sustainable transportation. Calculate and offset the carbon footprint of flights.
```
**Expected:** Should handle environmental considerations, specialized accommodations, carbon calculations

### Food & Culinary Journey
```
Design a 10-day culinary tour of Italy: cooking classes in Tuscany, wine tasting in Piedmont, street food in Naples, and Michelin dining in Rome. I'm gluten-free.
```
**Expected:** Should handle specialized interests, dietary restrictions, activity booking, regional planning


### Budget Backpacker Challenge
```
Plan a 3-week European backpacking trip for $800 total budget. Use only hostels, public transport, and free activities. Include Eastern Europe for better value.
```
**Expected:** Should handle extreme budget constraints, alternative accommodations, cost optimization

### Luxury Honeymoon with Surprises
```
Plan a surprise honeymoon to Maldives with overwater bungalows, private dining, spa treatments, and unique experiences like swimming with whale sharks. Budget unlimited but tasteful.
```
**Expected:** Should handle luxury planning, unique experiences, surprise elements, high-end services

### Business Conference & Networking
```
Attending a tech conference in Berlin next month. Need flights, hotels near the venue, networking event suggestions, and extend for 3 days to explore the startup scene.
```
**Expected:** Should handle business travel, event-based planning, networking opportunities, trip extension

###  Accessibility & Medical Needs
```
Plan a trip to Greece for someone with mobility issues using a wheelchair, diabetes requiring refrigerated medication, and severe food allergies. Include medical facility locations.
```
**Expected:** Should handle complex accessibility, medical requirements, safety planning, specialized research
