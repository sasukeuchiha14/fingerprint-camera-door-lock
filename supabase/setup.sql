-- =========================================
-- Fingerprint Camera Door Lock - Database Schema
-- =========================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================
-- USERS TABLE
-- Stores user information and authentication data
-- =========================================
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    fingerprint_id INTEGER UNIQUE, -- Slot number on fingerprint sensor (0-127)
    pin_code VARCHAR(4) NOT NULL, -- 4-digit password
    telegram_chat_id VARCHAR(50) UNIQUE, -- Telegram chat ID for notifications
    is_admin BOOLEAN DEFAULT FALSE, -- Admin privileges flag
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_access TIMESTAMP WITH TIME ZONE
);

-- =========================================
-- FACE_IMAGES TABLE
-- Stores URLs to face images in Supabase Storage
-- =========================================
CREATE TABLE IF NOT EXISTS face_images (
    image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    image_url TEXT NOT NULL, -- URL in Supabase Storage
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- ACCESS_LOGS TABLE
-- Stores all door access attempts
-- =========================================
CREATE TABLE IF NOT EXISTS access_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    access_type VARCHAR(50) NOT NULL, -- 'success', 'failed_password', 'failed_face', 'failed_fingerprint', 'break_in_attempt'
    authentication_method VARCHAR(50), -- 'password', 'face', 'fingerprint', 'combined'
    confidence_score FLOAT, -- Face recognition confidence or fingerprint confidence
    image_url TEXT, -- Capture image of the person
    notes TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- MODEL_METADATA TABLE
-- Tracks face recognition model versions
-- =========================================
CREATE TABLE IF NOT EXISTS model_metadata (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version VARCHAR(50) NOT NULL,
    model_url TEXT NOT NULL, -- URL to model file in Supabase Storage or VPS
    model_hash VARCHAR(64) NOT NULL, -- SHA-256 hash for integrity check
    training_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    num_users INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- SYSTEM_SETTINGS TABLE
-- General system configuration
-- =========================================
CREATE TABLE IF NOT EXISTS system_settings (
    setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- NOTIFICATIONS TABLE
-- Stores notifications to be sent via Telegram
-- =========================================
CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_type VARCHAR(50) NOT NULL, -- 'door_unlock', 'break_in', 'system_update', 'model_retrain'
    message TEXT NOT NULL,
    telegram_sent BOOLEAN DEFAULT FALSE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE
);

-- =========================================
-- INDEXES
-- =========================================
CREATE INDEX idx_users_fingerprint ON users(fingerprint_id);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_face_images_user ON face_images(user_id);
CREATE INDEX idx_access_logs_timestamp ON access_logs(timestamp DESC);
CREATE INDEX idx_access_logs_user ON access_logs(user_id);
CREATE INDEX idx_access_logs_type ON access_logs(access_type);
CREATE INDEX idx_model_active ON model_metadata(is_active);
CREATE INDEX idx_notifications_sent ON notifications(telegram_sent, created_at);

-- =========================================
-- TRIGGERS
-- =========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- ROW LEVEL SECURITY (RLS)
-- Enable RLS for security
-- =========================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access (for backend server)
CREATE POLICY "Service role has full access to users" ON users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to face_images" ON face_images
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to access_logs" ON access_logs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to model_metadata" ON model_metadata
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to system_settings" ON system_settings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to notifications" ON notifications
    FOR ALL USING (auth.role() = 'service_role');

-- =========================================
-- INITIAL SETTINGS DATA
-- =========================================
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
    ('max_login_attempts', '3', 'Maximum authentication attempts before lockout'),
    ('model_update_interval_hours', '24', 'Hours between model update checks'),
    ('telegram_notifications_enabled', 'true', 'Enable/disable Telegram notifications'),
    ('local_fallback_enabled', 'true', 'Enable local authentication when cloud is unavailable')
ON CONFLICT (setting_key) DO NOTHING;

-- =========================================
-- STORAGE BUCKETS
-- Create storage buckets (run this in Supabase dashboard SQL editor)
-- =========================================
-- INSERT INTO storage.buckets (id, name, public) VALUES 
--     ('face-images', 'face-images', false),
--     ('access-captures', 'access-captures', false),
--     ('face-models', 'face-models', false)
-- ON CONFLICT (id) DO NOTHING;

-- =========================================
-- STORAGE POLICIES
-- =========================================
-- CREATE POLICY "Service role can upload face images" ON storage.objects
--     FOR INSERT TO service_role WITH CHECK (bucket_id = 'face-images');

-- CREATE POLICY "Service role can read face images" ON storage.objects
--     FOR SELECT TO service_role USING (bucket_id = 'face-images');

-- CREATE POLICY "Service role can delete face images" ON storage.objects
--     FOR DELETE TO service_role USING (bucket_id = 'face-images');

-- CREATE POLICY "Service role can upload access captures" ON storage.objects
--     FOR INSERT TO service_role WITH CHECK (bucket_id = 'access-captures');

-- CREATE POLICY "Service role can upload models" ON storage.objects
--     FOR INSERT TO service_role WITH CHECK (bucket_id = 'face-models');

-- CREATE POLICY "Service role can read models" ON storage.objects
--     FOR SELECT TO service_role USING (bucket_id = 'face-models');

-- =========================================
-- HELPER FUNCTIONS
-- =========================================

-- Function to get active model
CREATE OR REPLACE FUNCTION get_active_model()
RETURNS TABLE (
    model_id UUID,
    model_version VARCHAR,
    model_url TEXT,
    model_hash VARCHAR,
    training_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT m.model_id, m.model_version, m.model_url, m.model_hash, m.training_date
    FROM model_metadata m
    WHERE m.is_active = TRUE
    ORDER BY m.training_date DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to create notification
CREATE OR REPLACE FUNCTION create_notification(
    p_notification_type VARCHAR,
    p_message TEXT,
    p_user_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_notification_id UUID;
BEGIN
    INSERT INTO notifications (notification_type, message, user_id)
    VALUES (p_notification_type, p_message, p_user_id)
    RETURNING notification_id INTO v_notification_id;
    
    RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log access attempt
CREATE OR REPLACE FUNCTION log_access_attempt(
    p_user_id UUID,
    p_access_type VARCHAR,
    p_authentication_method VARCHAR DEFAULT NULL,
    p_confidence_score FLOAT DEFAULT NULL,
    p_image_url TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO access_logs (
        user_id, 
        access_type, 
        authentication_method, 
        confidence_score, 
        image_url, 
        notes
    )
    VALUES (
        p_user_id, 
        p_access_type, 
        p_authentication_method, 
        p_confidence_score, 
        p_image_url, 
        p_notes
    )
    RETURNING log_id INTO v_log_id;
    
    -- Update user's last access time if successful
    IF p_access_type = 'success' THEN
        UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE user_id = p_user_id;
    END IF;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- VIEWS
-- =========================================

-- Recent access logs with user info
CREATE OR REPLACE VIEW recent_access_logs AS
SELECT 
    al.log_id,
    al.timestamp,
    al.access_type,
    al.authentication_method,
    al.confidence_score,
    u.name as user_name,
    u.email as user_email,
    al.notes
FROM access_logs al
LEFT JOIN users u ON al.user_id = u.user_id
ORDER BY al.timestamp DESC
LIMIT 100;

-- User statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    u.user_id,
    u.name,
    u.email,
    u.fingerprint_id,
    u.is_active,
    u.created_at,
    u.last_access,
    COUNT(fi.image_id) as face_images_count,
    COUNT(CASE WHEN al.access_type = 'success' THEN 1 END) as successful_access_count,
    COUNT(CASE WHEN al.access_type LIKE 'failed_%' THEN 1 END) as failed_access_count
FROM users u
LEFT JOIN face_images fi ON u.user_id = fi.user_id
LEFT JOIN access_logs al ON u.user_id = al.user_id
GROUP BY u.user_id, u.name, u.email, u.fingerprint_id, u.is_active, u.created_at, u.last_access;

-- =========================================
-- SAMPLE DATA (for testing)
-- =========================================
-- Uncomment to insert sample data

-- INSERT INTO users (name, email, phone, fingerprint_id, pin_code) VALUES
--     ('Hardik Garg', 'hardik@example.com', '+911234567890', 1, '1234'),
--     ('Test User', 'test@example.com', '+919876543210', 2, '5678');

-- =========================================
-- CONSTRAINTS AND VALIDATION
-- =========================================

-- Add PIN validation constraint
CREATE OR REPLACE FUNCTION validate_pin_code(pin TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- PIN must be exactly 4 digits
    RETURN pin ~ '^\d{4}$';
END;
$$ LANGUAGE plpgsql;

ALTER TABLE users ADD CONSTRAINT check_pin_format 
    CHECK (validate_pin_code(pin_code));

-- Add fingerprint ID range constraint (0-127 for R307 sensor)
ALTER TABLE users ADD CONSTRAINT check_fingerprint_id_range 
    CHECK (fingerprint_id >= 0 AND fingerprint_id <= 127);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- UTILITY FUNCTIONS
-- =========================================

-- Function to get next available fingerprint slot
CREATE OR REPLACE FUNCTION get_next_fingerprint_slot()
RETURNS INTEGER AS $$
DECLARE
    next_slot INTEGER;
BEGIN
    -- Find the first available slot from 1-127
    SELECT COALESCE(MIN(slot_num), 1) INTO next_slot
    FROM (
        SELECT generate_series(1, 127) AS slot_num
        EXCEPT
        SELECT fingerprint_id FROM users WHERE fingerprint_id IS NOT NULL
    ) available_slots;
    
    RETURN next_slot;
END;
$$ LANGUAGE plpgsql;

-- Function to get user images count
CREATE OR REPLACE FUNCTION get_user_images_count(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    image_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO image_count 
    FROM face_images 
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(image_count, 0);
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- STORAGE BUCKET SETUP INSTRUCTIONS
-- =========================================

/*
CRITICAL: You MUST create a storage bucket in Supabase for face images:

1. Go to your Supabase project dashboard
2. Navigate to Storage
3. Create a new bucket named "face-images"
4. Set bucket permissions as follows:

Bucket Configuration:
- Bucket name: face-images
- Public: Yes (or configure RLS policies)
- File size limit: 10MB
- Allowed MIME types: image/jpeg, image/png

Required Storage Policies:
CREATE POLICY "Allow public read access" ON storage.objects 
FOR SELECT USING (bucket_id = 'face-images');

CREATE POLICY "Allow authenticated uploads" ON storage.objects 
FOR INSERT WITH CHECK (bucket_id = 'face-images' AND auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated deletes" ON storage.objects 
FOR DELETE USING (bucket_id = 'face-images' AND auth.role() = 'authenticated');

Without this bucket, image uploads will fail!
*/

-- =========================================
-- END OF SETUP
-- =========================================
