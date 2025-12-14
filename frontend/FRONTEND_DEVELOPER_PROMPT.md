# Frontend Developer Agent Prompt - CarpoolWale

## Project Overview

You are building the frontend for **CarpoolWale**, a carpooling/ride-sharing application for India. The backend API is already implemented with FastAPI and PostgreSQL with PostGIS for geospatial features.

## Tech Stack Requirements

- **Framework**: React 18+ with TypeScript
- **Routing**: React Router v6
- **State Management**: Zustand or React Context + useReducer
- **Styling**: Tailwind CSS
- **Maps**: Leaflet or Google Maps API (for location selection and ride visualization)
- **HTTP Client**: Axios with interceptors for auth
- **Form Handling**: React Hook Form with Zod validation
- **Date/Time**: date-fns or dayjs
- **Build Tool**: Vite

## Project Structure

```
frontend/
├── src/
│   ├── api/                    # API client and endpoints
│   │   ├── client.ts           # Axios instance with interceptors
│   │   ├── auth.ts             # Auth API calls
│   │   ├── rides.ts            # Rides API calls
│   │   ├── vehicles.ts         # Vehicles API calls
│   │   └── users.ts            # User API calls
│   ├── components/
│   │   ├── common/             # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── Pagination.tsx
│   │   │   └── Toast.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignupForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── rides/
│   │   │   ├── RideCard.tsx
│   │   │   ├── RideList.tsx
│   │   │   ├── RideSearchForm.tsx
│   │   │   ├── PublishRideForm.tsx
│   │   │   ├── RideRequestCard.tsx
│   │   │   └── BookingCard.tsx
│   │   ├── vehicles/
│   │   │   ├── VehicleCard.tsx
│   │   │   ├── VehicleForm.tsx
│   │   │   └── VehicleList.tsx
│   │   ├── maps/
│   │   │   ├── LocationPicker.tsx
│   │   │   ├── RideMap.tsx
│   │   │   └── RouteDisplay.tsx
│   │   └── profile/
│   │       ├── ProfileCard.tsx
│   │       ├── ProfileEditForm.tsx
│   │       └── EmergencyContacts.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Login.tsx
│   │   ├── Signup.tsx
│   │   ├── Dashboard.tsx
│   │   ├── SearchRides.tsx
│   │   ├── PublishRide.tsx
│   │   ├── MyRides.tsx
│   │   ├── MyBookings.tsx
│   │   ├── RideDetails.tsx
│   │   ├── ManageRequests.tsx
│   │   ├── Vehicles.tsx
│   │   ├── Profile.tsx
│   │   └── NotFound.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useRides.ts
│   │   ├── useVehicles.ts
│   │   ├── useGeolocation.ts
│   │   └── usePagination.ts
│   ├── store/
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   ├── types/
│   │   ├── auth.ts
│   │   ├── ride.ts
│   │   ├── vehicle.ts
│   │   └── user.ts
│   ├── utils/
│   │   ├── formatters.ts       # Date, currency formatters
│   │   ├── validators.ts       # Zod schemas
│   │   ├── storage.ts          # LocalStorage helpers
│   │   └── constants.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── .env.example
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

## API Integration

### Base Configuration

```typescript
// src/api/client.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/v1';

// Auth header: 'Auth-Token' (not 'Authorization: Bearer')
// Token storage: localStorage

// Interceptors needed:
// 1. Request: Add Auth-Token header if token exists
// 2. Response: Handle 401 by attempting token refresh
// 3. Response: Handle token refresh failure by logging out
```

### API Endpoints Summary

| Feature | Method | Endpoint | Auth Required |
|---------|--------|----------|---------------|
| Signup | POST | `/users/signup` | No |
| Login | POST | `/users/login` | No |
| Logout | POST | `/users/logout` | Yes |
| Refresh Token | POST | `/users/refresh_token` | No |
| Get Profile | GET | `/users/profile` | Yes |
| Update Profile | PUT | `/users/profile` | Yes |
| Add Vehicle | POST | `/vehicles/add` | Yes |
| List Vehicles | GET | `/vehicles/list` | Yes |
| Get Vehicle | GET | `/vehicles/{id}` | Yes |
| Update Vehicle | PUT | `/vehicles/{id}` | Yes |
| Delete Vehicle | DELETE | `/vehicles/{id}` | Yes |
| Publish Ride | POST | `/rides/publish_ride` | Yes |
| Search Rides | GET | `/rides/view_rides` | Yes |
| Request Ride | POST | `/rides/request_ride` | Yes |
| My Rides | GET | `/rides/my_rides` | Yes |
| My Bookings | GET | `/rides/my_bookings` | Yes |
| Ride Requests | GET | `/rides/ride_requests/{ride_id}` | Yes |
| Respond Request | POST | `/rides/respond_request` | Yes |
| Cancel Ride | POST | `/rides/cancel_ride` | Yes |
| Cancel Booking | POST | `/rides/cancel_booking` | Yes |

## Core Features to Implement

### 1. Authentication Flow
- **Login Page**: Phone number + password login
- **Signup Page**: Full registration with emergency contacts
- **Token Management**: Store access_token and refresh_token in localStorage
- **Auto-refresh**: Implement token refresh on 401 responses
- **Protected Routes**: Redirect to login if not authenticated

### 2. Home / Dashboard
- Quick search form (origin, destination, date)
- Recent rides (if logged in)
- Call-to-action buttons for publishing and searching rides

### 3. Search Rides
- Location picker with map for origin and destination
- Date picker
- Vicinity/radius selector (1-100 km)
- Results list with pagination
- Each ride card shows:
  - Driver name
  - Origin → Destination
  - Date/time
  - Available seats
  - Price per seat
  - "Request" button

### 4. Publish Ride (Driver)
- Map-based origin/destination selection
- Optional additional stops (drag to reorder)
- Date/time picker for departure and arrival
- Seats and price input
- Vehicle selector (from user's vehicles)
- Additional notes textarea

### 5. My Rides (Driver Dashboard)
- Tabs: Active | Completed | Cancelled
- Each ride card shows:
  - Route details
  - Pending requests count (badge)
  - Confirmed passengers count
  - "Manage Requests" button
  - "Cancel Ride" button
- Pagination

### 6. Manage Ride Requests (Driver)
- List of passenger requests for a specific ride
- Each request shows:
  - Passenger name, phone, verification status
  - Seats requested
  - Accept/Reject buttons
- Real-time seat availability display

### 7. My Bookings (Passenger Dashboard)
- Tabs: All | Pending | Confirmed | Rejected | Cancelled
- Each booking shows:
  - Ride details
  - Driver name
  - Request status (with color coding)
  - "Cancel Booking" button (if not already cancelled)
- Pagination

### 8. Vehicles Management
- List of user's vehicles
- Add new vehicle form
- Edit vehicle
- Delete vehicle (with confirmation)

### 9. Profile
- View profile details
- Edit profile form
- Emergency contacts management

## UI/UX Requirements

### Design System
- **Primary Color**: Green (#22C55E) - represents eco-friendly carpooling
- **Secondary Color**: Blue (#3B82F6)
- **Error Color**: Red (#EF4444)
- **Warning Color**: Amber (#F59E0B)
- **Success Color**: Green (#22C55E)
- **Background**: Light gray (#F9FAFB)
- **Card Background**: White (#FFFFFF)

### Mobile-First Design
- Responsive breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Bottom navigation on mobile
- Sidebar navigation on desktop
- Touch-friendly tap targets (min 44px)

### Loading States
- Skeleton loaders for lists
- Spinner for buttons during API calls
- Disable form during submission

### Error Handling
- Toast notifications for errors
- Inline validation errors on forms
- Empty states for lists
- Network error handling with retry option

### Accessibility
- Proper ARIA labels
- Keyboard navigation
- Focus management in modals
- Color contrast compliance

## TypeScript Interfaces

```typescript
// src/types/auth.ts
interface User {
  id: number;
  first_name: string;
  last_name: string;
  phone_no: string;
  email?: string;
  bio?: string;
  profile_picture_url?: string;
  is_verified: boolean;
}

interface LoginRequest {
  phone_no: string;
  password: string;
  country_code?: string;
}

interface SignupRequest {
  first_name: string;
  last_name: string;
  phone_no: string;
  password: string;
  country_code?: string;
  email?: string;
  bio?: string;
  emergency_contact?: EmergencyContact[];
}

interface EmergencyContact {
  phone_no: string;
  name: string;
  country_code?: string;
  relationship?: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

// src/types/ride.ts
interface Coordinates {
  lat: number;
  lng: number;
}

interface Ride {
  id: number;
  ride_id: string;
  publisher_id: number;
  driver_name: string;
  origin: [number, number];
  destination: [number, number];
  start_datetime: string;
  end_datetime: string;
  available_seats: number;
  cost_per_seat: number;
  additional_note?: string;
}

interface MyRide extends Ride {
  is_active: boolean;
  is_cancelled: boolean;
  pending_requests: number;
  confirmed_passengers: number;
}

interface Booking {
  request_id: number;
  status: 'pending' | 'confirmed' | 'rejected' | 'cancelled';
  seats_requested: number;
  requested_at: string;
  ride_id: string;
  driver_name: string;
  origin: [number, number];
  destination: [number, number];
  start_datetime: string;
  end_datetime: string;
  cost_per_seat: number;
  ride_cancelled: boolean;
}

interface RideRequest {
  request_id: number;
  status: 'pending' | 'confirmed' | 'rejected' | 'cancelled';
  seats_requested: number;
  requested_at: string;
  passenger: {
    id: number;
    name: string;
    phone_no: string;
    profile_picture?: string;
    is_verified: boolean;
  };
}

interface PublishRideRequest {
  origin: [number, number];
  destination: [number, number];
  available_seats: number;
  cost_per_seat: number;
  additional_note?: string;
  additional_stop?: [number, number][];
  start_datetime: number; // epoch
  end_datetime: number; // epoch
  vehicle_id?: number;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// src/types/vehicle.ts
interface Vehicle {
  id: number;
  vehicle_type: 'car' | 'bike' | 'auto' | 'suv' | 'van' | 'bus';
  make?: string;
  model?: string;
  color?: string;
  license_plate: string;
  max_capacity: number;
  created_at: string;
}

interface VehicleFormData {
  vehicle_type: string;
  make?: string;
  model?: string;
  color?: string;
  license_plate: string;
  max_capacity: number;
}
```

## Validation Schemas (Zod)

```typescript
// src/utils/validators.ts
import { z } from 'zod';

export const loginSchema = z.object({
  phone_no: z.string().min(10).max(15),
  password: z.string().min(1),
  country_code: z.string().default('+91'),
});

export const signupSchema = z.object({
  first_name: z.string().min(1).max(50),
  last_name: z.string().min(1).max(50),
  phone_no: z.string().min(10).max(15),
  password: z
    .string()
    .min(8)
    .regex(/[A-Za-z]/, 'Must contain a letter')
    .regex(/\d/, 'Must contain a number'),
  email: z.string().email().optional().or(z.literal('')),
  bio: z.string().max(500).optional(),
});

export const publishRideSchema = z.object({
  origin: z.tuple([z.number().min(-90).max(90), z.number().min(-180).max(180)]),
  destination: z.tuple([z.number().min(-90).max(90), z.number().min(-180).max(180)]),
  available_seats: z.number().min(1).max(50),
  cost_per_seat: z.number().min(0).max(100000),
  start_datetime: z.number(),
  end_datetime: z.number(),
  additional_note: z.string().max(500).optional(),
  vehicle_id: z.number().optional(),
}).refine(data => data.end_datetime > data.start_datetime, {
  message: 'End time must be after start time',
});

export const vehicleSchema = z.object({
  vehicle_type: z.enum(['car', 'bike', 'auto', 'suv', 'van', 'bus']),
  make: z.string().max(50).optional(),
  model: z.string().max(50).optional(),
  color: z.string().max(30).optional(),
  license_plate: z.string().min(1).max(20),
  max_capacity: z.number().min(1).max(50),
});
```

## Environment Variables

```env
# .env.example
VITE_API_URL=http://localhost:8000/v1
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_key
# OR for Leaflet (free)
VITE_USE_LEAFLET=true
```

## Key Implementation Notes

1. **Coordinates Format**: Backend expects `[latitude, longitude]` arrays
2. **Timestamps**: Send as Unix epoch (seconds), display human-readable
3. **Auth Header**: Use `Auth-Token` header, not `Authorization: Bearer`
4. **Pagination**: All list endpoints return `{ items, total, page, per_page, total_pages }`
5. **Error Format**: Errors come as `{ error: "message" }` or `{ detail: "validation error" }`
6. **Indian Localization**:
   - Default country code: +91
   - Currency: INR (₹)
   - Date format: DD Month YYYY, HH:MM

## Getting Started

1. Initialize project: `npm create vite@latest . -- --template react-ts`
2. Install dependencies:
   ```bash
   npm install axios react-router-dom zustand react-hook-form @hookform/resolvers zod date-fns leaflet react-leaflet @types/leaflet
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```
3. Configure Tailwind CSS
4. Set up API client with interceptors
5. Implement auth store and protected routes
6. Build pages incrementally

## Priority Order

1. **Phase 1 - Auth & Core**
   - Login/Signup pages
   - Auth store with token management
   - Protected routes
   - Basic layout with header/navigation

2. **Phase 2 - Ride Search**
   - Home page with search form
   - Search results page with map
   - Request ride functionality

3. **Phase 3 - Driver Features**
   - Publish ride page
   - My rides dashboard
   - Manage requests page

4. **Phase 4 - Passenger Features**
   - My bookings page
   - Booking cancellation

5. **Phase 5 - Profile & Vehicles**
   - Profile page with edit
   - Vehicles management

6. **Phase 6 - Polish**
   - Loading states
   - Error handling
   - Mobile responsiveness
   - Accessibility improvements

---

**Backend API Documentation**: See `../backend/API_DOCUMENTATION.md` for complete API reference.