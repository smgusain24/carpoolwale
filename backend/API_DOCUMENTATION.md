# CarpoolWale Backend API Documentation

## Base URL
```
http://localhost:8000/v1
```

## Authentication
All protected endpoints require the `Auth-Token` header with a valid JWT access token.

```
Auth-Token: <access_token>
```

---

## Endpoints

### Authentication & Users

#### POST `/users/signup`
Register a new user.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone_no": "9876543210",
  "password": "SecurePass123",
  "country_code": "+91",
  "email": "john@example.com",
  "bio": "Regular commuter",
  "emergency_contact": [
    {
      "phone_no": "9876543211",
      "name": "Jane Doe",
      "country_code": "+91",
      "relationship": "spouse"
    }
  ]
}
```

**Validation Rules:**
- `first_name`, `last_name`: 1-50 characters
- `phone_no`: 10-15 digits
- `password`: min 8 chars, must contain at least one letter and one digit
- `email`: valid email format (optional)
- `bio`: max 500 characters (optional)
- `emergency_contact`: max 5 contacts (optional)

**Response (201):**
```json
{
  "msg": "User created successfully",
  "user_id": 1
}
```

---

#### POST `/users/login`
Authenticate user and get tokens.

**Request Body:**
```json
{
  "phone_no": "9876543210",
  "password": "SecurePass123",
  "country_code": "+91"
}
```

**Response (200):**
```json
{
  "msg": "Login successful",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_no": "9876543210",
    "email": "john@example.com"
  }
}
```

---

#### POST `/users/logout`
Revoke current session. **Requires Auth**

**Response (200):**
```json
{
  "msg": "Logged out successfully"
}
```

---

#### POST `/users/refresh_token`
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

---

#### GET `/users/profile`
Get current user profile. **Requires Auth**

**Response (200):**
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "phone_no": "9876543210",
  "email": "john@example.com",
  "bio": "Regular commuter",
  "profile_picture_url": null,
  "is_verified": false
}
```

---

#### PUT `/users/profile`
Update user profile. **Requires Auth**

**Request Body (all fields optional):**
```json
{
  "first_name": "Johnny",
  "last_name": "Doe",
  "email": "johnny@example.com",
  "bio": "Updated bio",
  "profile_picture_url": "https://..."
}
```

**Validation Rules:**
- `first_name`, `last_name`: 1-50 characters
- `bio`: max 500 characters
- `profile_picture_url`: max 500 characters

**Response (200):**
```json
{
  "msg": "Profile updated successfully"
}
```

---

### Vehicles

#### POST `/vehicles/add`
Add a new vehicle. **Requires Auth**

**Request Body:**
```json
{
  "vehicle_type": "car",
  "make": "Toyota",
  "model": "Camry",
  "color": "White",
  "license_plate": "MH12AB1234",
  "max_capacity": 4
}
```

**Validation Rules:**
- `vehicle_type`: one of `car`, `bike`, `auto`, `suv`, `van`, `bus`
- `make`, `model`: max 50 characters (optional)
- `color`: max 30 characters (optional)
- `license_plate`: 1-20 characters, alphanumeric only
- `max_capacity`: 1-50

**Response (201):**
```json
{
  "msg": "Vehicle added successfully",
  "vehicle_id": 1
}
```

---

#### GET `/vehicles/list`
Get all vehicles for current user. **Requires Auth**

**Response (200):**
```json
{
  "vehicles": [
    {
      "id": 1,
      "vehicle_type": "car",
      "make": "Toyota",
      "model": "Camry",
      "color": "White",
      "license_plate": "MH12AB1234",
      "max_capacity": 4,
      "created_at": "14 December 2024"
    }
  ]
}
```

---

#### GET `/vehicles/{vehicle_id}`
Get specific vehicle details. **Requires Auth**

**Response (200):**
```json
{
  "vehicle": {
    "id": 1,
    "user_id": 1,
    "vehicle_type": "car",
    "make": "Toyota",
    "model": "Camry",
    "color": "White",
    "license_plate": "MH12AB1234",
    "max_capacity": 4,
    "created_at": "14 December 2024"
  }
}
```

---

#### PUT `/vehicles/{vehicle_id}`
Update a vehicle. **Requires Auth**

**Request Body (all fields optional):**
```json
{
  "vehicle_type": "suv",
  "make": "Toyota",
  "model": "Fortuner",
  "color": "Black",
  "license_plate": "MH12CD5678",
  "max_capacity": 6
}
```

**Response (200):**
```json
{
  "msg": "Vehicle updated successfully"
}
```

---

#### DELETE `/vehicles/{vehicle_id}`
Delete a vehicle (soft delete). **Requires Auth**

**Response (200):**
```json
{
  "msg": "Vehicle deleted successfully"
}
```

---

### Rides

#### POST `/rides/publish_ride`
Publish a new ride as driver. **Requires Auth**

**Request Body:**
```json
{
  "origin": [19.0760, 72.8777],
  "destination": [18.5204, 73.8567],
  "available_seats": 3,
  "cost_per_seat": 250.00,
  "additional_note": "AC car, comfortable ride",
  "additional_stop": [[19.0330, 73.0297]],
  "start_datetime": 1702900800,
  "end_datetime": 1702908000,
  "vehicle_id": 1
}
```

**Field Descriptions:**
- `origin`: `[latitude, longitude]` - Starting point
- `destination`: `[latitude, longitude]` - End point
- `available_seats`: Number of seats available (1-50)
- `cost_per_seat`: Price per seat in INR (0-100000)
- `additional_note`: Notes about the ride (max 500 chars, optional)
- `additional_stop`: Array of `[lat, lng]` stops (max 10, optional)
- `start_datetime`: Unix epoch timestamp for departure
- `end_datetime`: Unix epoch timestamp for estimated arrival
- `vehicle_id`: ID of vehicle to use (optional, must belong to user)

**Validation Rules:**
- Coordinates: lat (-90 to 90), lng (-180 to 180)
- `end_datetime` must be after `start_datetime`
- `start_datetime` cannot be in the past
- If `vehicle_id` provided, `available_seats` cannot exceed vehicle's `max_capacity`

**Response (200):**
```json
{
  "msg": "Ride published successfully",
  "ride_id": "a1b2c3d4e5f6..."
}
```

---

#### GET `/rides/view_rides`
Search available rides. **Requires Auth**

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `epoch_date` | int | Yes | - | Date to search (Unix timestamp) |
| `origin` | string | Yes | - | JSON array `[lat, lng]` |
| `destination` | string | Yes | - | JSON array `[lat, lng]` |
| `vicinity` | int | No | 10 | Search radius in km (1-100) |
| `page` | int | No | 1 | Page number |
| `per_page` | int | No | 20 | Items per page (1-100) |

**Example:**
```
GET /rides/view_rides?epoch_date=1702900800&origin=[19.0760,72.8777]&destination=[18.5204,73.8567]&vicinity=15&page=1&per_page=10
```

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "ride_id": "a1b2c3d4e5f6...",
      "publisher_id": 2,
      "driver_name": "Jane Smith",
      "origin": [19.0760, 72.8777],
      "destination": [18.5204, 73.8567],
      "start_datetime": "18 December 2024, 08:00",
      "end_datetime": "18 December 2024, 10:00",
      "available_seats": 3,
      "cost_per_seat": 250.00,
      "additional_note": "AC car, comfortable ride"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 10,
  "total_pages": 3
}
```

---

#### POST `/rides/request_ride`
Request to join a ride as passenger. **Requires Auth**

**Request Body:**
```json
{
  "ride_id": "a1b2c3d4e5f6...",
  "seats_requested": 2,
  "pickup_location": [19.0500, 72.8800],
  "dropoff_location": [18.5300, 73.8600]
}
```

**Validation Rules:**
- `ride_id`: 1-100 characters
- `seats_requested`: 1-50 (default: 1)
- `pickup_location`, `dropoff_location`: valid coordinates (optional)

**Response (201):**
```json
{
  "msg": "Ride requested successfully",
  "ride_id": "a1b2c3d4e5f6..."
}
```

**Error Responses:**
- 404: Ride not found
- 400: Ride not active, not enough seats, already requested, or requesting own ride

---

#### GET `/rides/my_rides`
Get rides published by current user (as driver). **Requires Auth**

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `active` | Filter: `active`, `completed`, `cancelled`, `all` |
| `page` | int | No | 1 | Page number |
| `per_page` | int | No | 20 | Items per page (1-100) |

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "ride_id": "a1b2c3d4e5f6...",
      "origin": [19.0760, 72.8777],
      "destination": [18.5204, 73.8567],
      "start_datetime": "18 December 2024, 08:00",
      "end_datetime": "18 December 2024, 10:00",
      "available_seats": 3,
      "cost_per_seat": 250.00,
      "is_active": true,
      "is_cancelled": false,
      "pending_requests": 2,
      "confirmed_passengers": 1
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

---

#### GET `/rides/my_bookings`
Get rides where current user is a passenger. **Requires Auth**

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `all` | Filter: `pending`, `confirmed`, `rejected`, `cancelled`, `all` |
| `page` | int | No | 1 | Page number |
| `per_page` | int | No | 20 | Items per page (1-100) |

**Response (200):**
```json
{
  "items": [
    {
      "request_id": 1,
      "status": "confirmed",
      "seats_requested": 2,
      "requested_at": "14 December 2024, 10:30",
      "ride_id": "a1b2c3d4e5f6...",
      "driver_name": "Jane Smith",
      "origin": [19.0760, 72.8777],
      "destination": [18.5204, 73.8567],
      "start_datetime": "18 December 2024, 08:00",
      "end_datetime": "18 December 2024, 10:00",
      "cost_per_seat": 250.00,
      "ride_cancelled": false
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

---

#### GET `/rides/ride_requests/{ride_id}`
Get all passenger requests for a specific ride. **Requires Auth (Driver only)**

**Response (200):**
```json
{
  "requests": [
    {
      "request_id": 1,
      "status": "pending",
      "seats_requested": 2,
      "requested_at": "14 December 2024, 10:30",
      "passenger": {
        "id": 3,
        "name": "John Doe",
        "phone_no": "9876543210",
        "profile_picture": null,
        "is_verified": false
      }
    }
  ]
}
```

---

#### POST `/rides/respond_request`
Accept or reject a ride request. **Requires Auth (Driver only)**

**Request Body:**
```json
{
  "request_id": 1,
  "action": "accept"
}
```

**Validation:**
- `action`: must be `accept` or `reject`

**Response (200):**
```json
{
  "msg": "Request accepted successfully"
}
```

---

#### POST `/rides/cancel_ride`
Cancel a published ride. **Requires Auth (Driver only)**

**Request Body:**
```json
{
  "ride_id": "a1b2c3d4e5f6..."
}
```

**Response (200):**
```json
{
  "msg": "Ride cancelled successfully"
}
```

*Note: Cancelling a ride automatically cancels all pending and confirmed passenger bookings.*

---

#### POST `/rides/cancel_booking`
Cancel a ride booking. **Requires Auth (Passenger only)**

**Request Body:**
```json
{
  "request_id": 1
}
```

**Response (200):**
```json
{
  "msg": "Booking cancelled successfully"
}
```

*Note: If booking was confirmed, seats are restored to the ride's available count.*

---

### System

#### GET `/health`
Health check endpoint.

**Response (200):**
```json
{
  "status": "healthy"
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error message here"
}
```

Or for validation errors:

```json
{
  "detail": "Validation error details"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Not authorized for this action |
| 404 | Not Found |
| 422 | Unprocessable Entity - Validation failed |
| 500 | Internal Server Error |

---

## Data Types

### Coordinates
All coordinates are represented as `[latitude, longitude]` arrays:
- Latitude: -90 to 90
- Longitude: -180 to 180

### Timestamps
- Request timestamps: Unix epoch (seconds)
- Response timestamps: Human-readable format "DD Month YYYY, HH:MM"

### Pagination Response
All paginated endpoints return:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "total_pages": 5
}
```

---

## Rate Limits

Currently no rate limiting is implemented. Recommended for production:
- Authentication endpoints: 5 requests/minute
- Other endpoints: 60 requests/minute

---

## WebSocket (Future)

Real-time notifications are planned for:
- Ride request received (for drivers)
- Request accepted/rejected (for passengers)
- Ride cancelled
- Ride starting soon reminders
