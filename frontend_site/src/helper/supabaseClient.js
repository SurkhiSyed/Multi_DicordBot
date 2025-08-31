import { createClient } from '@supabase/supabase-js';

const supabaseURL = "https://cswqvcabjksyafhzkrew.supabase.co";
const supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzd3F2Y2FiamtzeWFmaHprcmV3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2MDExMzMsImV4cCI6MjA3MjE3NzEzM30.p0gUVztzBvVqRqy1FL5k2fIIhizy8bbkaY6BeWc7IWQ"

const supabase = createClient(supabaseURL, supabaseAnonKey);

export default supabase;    