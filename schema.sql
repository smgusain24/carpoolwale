-- Create extensions for additional functionality
CREATE EXTENSION IF NOT EXISTS postgis;  -- For geographical data
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- For cryptographic functions

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(55) NOT NULL,
    last_name VARCHAR(55) NOT NULL,
    country_code VARCHAR(5) NOT NULL DEFAULT '+91',
    phone_no VARCHAR(10) NOT NULL,
    email VARCHAR(255) NULL,
    hashed_password BYTEA NOT NULL,
    bio TEXT,
    profile_picture_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(phone_no, country_code),
    UNIQUE(email)
);

-- Emergency contacts table
CREATE TABLE emergency_contacts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(55) NOT NULL,
    country_code VARCHAR(5) NOT NULL DEFAULT '+91',
    phone_no VARCHAR(10) NOT NULL,
    relationship VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Vehicles table
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    color VARCHAR(30),
    license_plate VARCHAR(20) NOT NULL,
    max_capacity INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Rides table
CREATE TABLE rides (
    id SERIAL PRIMARY KEY,
    ride_id VARCHAR(64) NOT NULL UNIQUE,  -- Generated unique identifier
    publisher_id INT NOT NULL,
    origin GEOGRAPHY(POINT, 4326) NOT NULL,  -- Using PostGIS geography type for coordinates
    destination GEOGRAPHY(POINT, 4326) NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    available_seats INT NOT NULL,
    cost_per_seat DECIMAL(10, 2),
    additional_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_cancelled BOOLEAN NOT NULL DEFAULT FALSE,
    vehicle_id INT NOT NULL
);

-- Additional stops table
CREATE TABLE additional_stops (
    id SERIAL PRIMARY KEY,
    ride_id INT NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    sequence_order INT NOT NULL,  -- Order of stops
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Ride passengers (requests and confirmed passengers)
CREATE TABLE ride_passengers (
    id SERIAL PRIMARY KEY,
    ride_id INT NOT NULL,
    passenger_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    seats_requested INT NOT NULL DEFAULT 1,
    pickup_location GEOGRAPHY(POINT, 4326),  -- Optional custom pickup location
    dropoff_location GEOGRAPHY(POINT, 4326),  -- Optional custom dropoff location
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Ratings and reviews
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    ride_id INT NOT NULL,
    rater_id INT NOT NULL,
    rated_user_id INT NOT NULL,
    rating INT NOT NULL,
    review TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- User verification documents
CREATE TABLE verification_documents (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- ID card, driver's license, etc.
    document_url TEXT NOT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMP,
    reason TEXT,  -- Reason for rejection if applicable
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    ride_id INT NOT NULL,
    payer_id INT NOT NULL,
    payee_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- User sessions/tokens table
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(255) NOT NULL,
    token_jti VARCHAR(36),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMP,
    device_info TEXT,
    ip_address VARCHAR(45),
    token_jti varchar(36) NOT NULL,
	revoked bool DEFAULT false NULL,
	revoked_at timestamp NULL,
    UNIQUE(refresh_token)
);

-- Create indexes for performance (without foreign key constraints)
CREATE INDEX idx_emergency_contacts_user_id ON emergency_contacts(user_id);
CREATE INDEX idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX idx_rides_publisher_id ON rides(publisher_id);
CREATE INDEX idx_rides_datetime ON rides(start_datetime, end_datetime);
CREATE INDEX idx_rides_active_cancelled ON rides(is_active, is_cancelled);
CREATE INDEX idx_additional_stops_ride_id ON additional_stops(ride_id);
CREATE INDEX idx_ride_passengers_ride_id ON ride_passengers(ride_id);
CREATE INDEX idx_ride_passengers_passenger_id ON ride_passengers(passenger_id);
CREATE INDEX idx_ride_passengers_status ON ride_passengers(status);
CREATE INDEX idx_ratings_ride_id ON ratings(ride_id);
CREATE INDEX idx_ratings_rated_user_id ON ratings(rated_user_id);
CREATE INDEX idx_verification_documents_user_id ON verification_documents(user_id);
CREATE INDEX idx_payments_ride_id ON payments(ride_id);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Create spatial indexes for geospatial queries
CREATE INDEX idx_rides_origin ON rides USING GIST(origin);
CREATE INDEX idx_rides_destination ON rides USING GIST(destination);
CREATE INDEX idx_additional_stops_location ON additional_stops USING GIST(location);
CREATE INDEX idx_ride_passengers_pickup ON ride_passengers USING GIST(pickup_location);
CREATE INDEX idx_ride_passengers_dropoff ON ride_passengers USING GIST(dropoff_location);