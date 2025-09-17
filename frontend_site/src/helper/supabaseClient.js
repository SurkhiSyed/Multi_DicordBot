import { createClient } from '@supabase/supabase-js';

const supabaseURL = [supabaseUrl];
const supabaseAnonKey = [supabaseAnonKey];

const supabase = createClient(supabaseURL, supabaseAnonKey);

export default supabase;    
