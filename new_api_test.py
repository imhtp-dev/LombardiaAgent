@tool
async def select_health_center(
    health_center_uuid: str,
    user_id: str,
    selected_service_uuid: str,
    additional_services_data: str = ""
) -> str:
    """
    Manages the patient's health center selection and calls the health-service API.
    
    Args:
        health_center_uuid: UUID of the health center chosen by the patient
        user_id: User/chat ID
        selected_service_uuid: UUID of the main selected service
        additional_services_data: Additional services in format "uuid1:sector1,uuid2:sector2" (optional)
    
    Returns:
        API call result or error message
    """
    print(f"🏥 Tool select_health_center called - selected center: {health_center_uuid}")
    print(f"👤 User ID: {user_id}")
    
    try:
        print(f"📋 Received parameters:")
        print(f"   selected_service_uuid: {selected_service_uuid}")
        print(f"   additional_services_data: {additional_services_data}")
        
        # Initialize all API fields
        health_services = "9a93d65f-396a-45e4-9284-94481bdd2b51"
        prescriptions = ""
        preliminary_visits = ""
        optionals = "ea65a7bf-58e4-4ac0-9041-61a5088cefb6"
        opinions = ""
        
        # Use a set to avoid duplicates in each field
        health_services_set = {selected_service_uuid}  # Initialize with the main service
        prescriptions_set = set()
        preliminary_visits_set = set()
        optionals_set = set()
        opinions_set = set()
        
        # Process additional services if present
        if additional_services_data:
            # Format: "uuid1:sector1,uuid2:sector2,uuid3:sector3"
            service_pairs = additional_services_data.split(",")
            for pair in service_pairs:
                if ":" in pair:
                    service_uuid, sector = pair.split(":", 1)
                    
                    if sector == "AMB" or sector == "health_services":
                        health_services_set.add(service_uuid)
                    elif sector == "prescriptions":
                        prescriptions_set.add(service_uuid)
                    elif sector == "preliminary_visits":
                        preliminary_visits_set.add(service_uuid)
                    elif sector == "optionals":
                        optionals_set.add(service_uuid)
                    elif sector == "opinions":
                        opinions_set.add(service_uuid)
                    else:
                        # Default: everything goes to health_services
                        health_services_set.add(service_uuid)
        
        # Convert sets to comma-separated strings
        health_services = ",".join(sorted(health_services_set)) if health_services_set else ""
        prescriptions = ",".join(sorted(prescriptions_set)) if prescriptions_set else ""
        preliminary_visits = ",".join(sorted(preliminary_visits_set)) if preliminary_visits_set else ""
        optionals = ",".join(sorted(optionals_set)) if optionals_set else ""
        opinions = ",".join(sorted(opinions_set)) if opinions_set else ""
        
        # Get the token for the API
        token = await get_tokenn()
        
        # Prepare the API call
        api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/sort/health-center/{health_center_uuid}/health-service'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        request_data = {
            'gender': 'm',  # Hardcoded as requested
            'date_of_birth': '1980-04-13',  # Hardcoded as requested
            'health_services': health_services,
            'prescriptions': prescriptions,
            'preliminary_visits': preliminary_visits,
            'optionals': optionals,
            'opinions': opinions
        }
        
        print(f"📊 === SECTORS EXTRACTION ===")
        print(f"   health_services: {health_services}")
        print(f"   prescriptions: {prescriptions}")
        print(f"   preliminary_visits: {preliminary_visits}")
        print(f"   optionals: {optionals}")
        print(f"   opinions: {opinions}")
        
        print(f"📡 health-service API call:")
        print(f"   URL: {api_url}")
        print(f"   health_center_uuid: {health_center_uuid}")
        print(f"   Headers: {headers}")
        print(f"   === REQUEST_DATA PARAMETERS ===")
        print(f"   gender: {request_data['gender']}")
        print(f"   date_of_birth: {request_data['date_of_birth']}")
        print(f"   health_services: {request_data['health_services']}")
        print(f"   prescriptions: {request_data['prescriptions']}")
        print(f"   preliminary_visits: {request_data['preliminary_visits']}")
        print(f"   optionals: {request_data['optionals']}")
        print(f"   opinions: {request_data['opinions']}")
        print(f"   === COMPLETE JSON DATA ===")
        print(f"   {request_data}")
        
        # Make the API request
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ health-service API: success - data received")
                    print(f"📊 API Response: {data}")
                    
                    # =====================================================================
                    # PACKAGE DETECTION AND SERVICE REPLACEMENT LOGIC
                    # =====================================================================
                    
                    # Check if there are packages (different UUIDs than requested)
                    package_detected = False
                    if data and isinstance(data, list) and len(data) > 0:
                        response_services = data[0].get('health_services', [])
                        
                        if response_services:
                            print(f"🔍 === PACKAGE ANALYSIS ===")
                            
                            # Collect all requested UUIDs
                            requested_uuids = set()
                            requested_uuids.add(selected_service_uuid)
                            if additional_services_data:
                                service_pairs = additional_services_data.split(",")
                                for pair in service_pairs:
                                    if ":" in pair:
                                        service_uuid, _ = pair.split(":", 1)
                                        requested_uuids.add(service_uuid.strip())
                            
                            # Collect all UUIDs in the response
                            response_uuids = set()
                            for service in response_services:
                                if isinstance(service, dict) and 'uuid' in service:
                                    response_uuids.add(service['uuid'])
                            
                            print(f"📋 Requested UUIDs: {requested_uuids}")
                            print(f"📋 UUIDs in response: {response_uuids}")
                            
                            # Check differences
                            if requested_uuids != response_uuids:
                                package_detected = True
                                missing_in_response = requested_uuids - response_uuids
                                additional_in_response = response_uuids - requested_uuids
                                
                                print(f"🎁 === PACKAGE DETECTED ===")
                                print(f"   Services missing in response: {missing_in_response}")
                                print(f"   Additional services in response: {additional_in_response}")
                                
                                # LOG: Inform the user about the replacement (optional)
                                if missing_in_response or additional_in_response:
                                    print(f"📢 The center offers an alternative package")
                                    print(f"📢 Replacing services with those from the package")
                                    
                                    # TODO: Here you should update the session state
                                    # to replace the original services with those from the package
                                    # 
                                    # Example of how you could do it:
                                    # await update_session_services(user_id, response_services)
                                    #
                                    # For now, logging information for debug
                                    services_info = []
                                    for service in response_services:
                                        if isinstance(service, dict):
                                            service_name = service.get('name', 'N/A')
                                            service_uuid = service.get('uuid', 'N/A')
                                            services_info.append(f"{service_name} ({service_uuid})")
                                    
                                    print(f"📋 Services in package: {services_info}")
                    
                    # Return message with package information
                    success_message = "Health center successfully selected!"
                    if package_detected:
                        success_message += " The center has offered an optimized service package."
                    success_message += " Now let's proceed with choosing the date and time for your appointment."
                    
                    # Serialize the API response to include it in the return while maintaining structure and order
                    import json
                    api_response_json = json.dumps(data, ensure_ascii=False)
                    
                    return f"HEALTH_CENTER_SELECTED|{health_center_uuid}|{success_message}|{api_response_json}"
                    
                else:
                    print(f"❌ health-service API error: {response.status}")
                    response_text = await response.text()
                    print(f"   Response: {response_text}")
                    return f"ERROR|Error during health center selection (code: {response.status})"
                    
    except Exception as e:
        print(f"❌ Error in select_health_center: {e}")
        return f"ERROR|Internal error during center selection: {str(e)}"