-- InBrief Database Schema for Supabase
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS news_post (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    author VARCHAR(200),
    source_url TEXT
);

-- Create some sample data for testing
INSERT INTO news_post (title, content, author) VALUES 
('Welcome to InBrief!', 'This is your new independent news application powered by Supabase. You are now completely independent from Railway infrastructure.', 'System'),
('Database Migration Complete', 'Successfully migrated from Railway to Supabase for better reliability. All your data is now hosted on Supabase with excellent global connectivity.', 'Admin'),
('Netlify Deployment Active', 'The application is now running on Netlify with Supabase database. This setup should resolve all domain blocking issues.', 'DevOps'),
('Testing Post with Image', 'This is a test post to verify that all functionality works correctly.', 'Developer'),
('Network Connectivity Fixed', 'The new Netlify + Supabase setup should work on all networks, including mobile data and corporate networks.', 'Network Team');

-- Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_news_post_created_at ON news_post(created_at DESC);
