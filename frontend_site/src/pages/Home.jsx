import React, { useState, useEffect } from 'react'
import supabase from '../helper/supabaseClient'

// Icons (keep all your existing icons)
const SearchIcon = ({ className = "w-5 h-5" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const ExternalLinkIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
);

const BriefcaseIcon = ({ className = "w-5 h-5" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2-2v2m8 0V6a2 2 0 012 2v6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m-8 0V6a2 2 0 00-2 2v6.341" />
  </svg>
);

const UserIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const LogoutIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

const ChevronLeftIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
  </svg>
);

const ChevronRightIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

// Status configuration
const STATUS_CONFIG = {
  not_applied: { label: 'Not Applied', color: 'bg-gray-100 text-gray-800', dotColor: 'bg-gray-400' },
  applied: { label: 'Applied', color: 'bg-blue-100 text-blue-800', dotColor: 'bg-blue-400' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800', dotColor: 'bg-red-400' },
  interview: { label: 'Interview', color: 'bg-yellow-100 text-yellow-800', dotColor: 'bg-yellow-400' },
  offer: { label: 'Offer', color: 'bg-green-100 text-green-800', dotColor: 'bg-green-400' }
};

function Home() {
  const [jobs, setJobs] = useState([]);
  const [userJobs, setUserJobs] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total: 0, total_pages: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingUserJobs, setIsLoadingUserJobs] = useState(false);
  const [user, setUser] = useState(null);
  const [searchConfig, setSearchConfig] = useState({
    username: '',
    password: '',
    numJobs: 56,
    searchTitle: 'intern',
    location: ''
  });

  // Get current user session
  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser(session.user);
        console.log('Current user:', session.user.id, session.user.email);
      }
    };

    getUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        setUser(session.user);
      } else {
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSearchConfigChange = (field, value) => {
    setSearchConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const handleStatusChange = async (jobId, newStatus) => {
    try {
      const response = await fetch(`http://localhost:8000/api/user-jobs/${user.id}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobId,
          status: newStatus
        })
      });

      const data = await response.json();
      
      if (data.success) {
        // Update the job status in local state
        setUserJobs(prevJobs =>
          prevJobs.map(job =>
            job.id === jobId
              ? { ...job, application_status: newStatus }
              : job
          )
        );
        console.log(`✅ Updated job ${jobId} status to ${newStatus}`);
      } else {
        alert(`Failed to update status: ${data.error}`);
      }
    } catch (error) {
      console.error('❌ Error updating job status:', error);
      alert('Failed to update job status');
    }
  };

  const handleFetchJobs = async () => {
    console.log('🔍 handleFetchJobs called');
    
    if (!user?.id) {
      alert('User session not found. Please try logging out and back in.');
      return;
    }

    if (!searchConfig.username || !searchConfig.password) {
      alert('Please enter your LinkedIn credentials');
      return;
    }

    setIsLoading(true);
    
    try {
      const requestBody = {
        linkedin_username: searchConfig.username,
        linkedin_password: searchConfig.password,
        num_jobs: searchConfig.numJobs,
        user_id: user.id
      };

      console.log('📤 Making request to /api/jobs');

      const response = await fetch(`http://localhost:8000/api/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setJobs(data.jobs);
        console.log(`✅ Set ${data.jobs.length} jobs in state`);
        
        if (data.database) {
          alert(`Scraping completed!\nScraped: ${data.total_jobs} jobs\nSaved to DB: ${data.database.saved} new jobs\nDuplicates: ${data.database.duplicates}`);
        }
        await fetchUserJobs(1); // Refresh user jobs
      } else {
        console.error('❌ API returned error:', data.error);
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('❌ Error fetching jobs:', error);
      alert(`Failed to fetch jobs: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserJobs = async (page = 1) => {
    if (!user?.id) return;

    setIsLoadingUserJobs(true);
    try {
      console.log(`📚 Fetching user jobs from database (page ${page})...`);
      const response = await fetch(`http://localhost:8000/api/user-jobs/${user.id}?page=${page}&limit=50`);
      const data = await response.json();
      
      if (data.success) {
        setUserJobs(data.jobs);
        setPagination(data.pagination);
        console.log(`✅ Fetched ${data.jobs.length} saved jobs for user (page ${page}/${data.pagination.total_pages})`);
      } else {
        console.error('❌ Failed to fetch user jobs:', data.error);
      }
    } catch (error) {
      console.error('❌ Error fetching user jobs:', error);
    } finally {
      setIsLoadingUserJobs(false);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      fetchUserJobs(newPage);
    }
  };

  // Fetch user jobs when user logs in
  useEffect(() => {
    if (user?.id) {
      fetchUserJobs(1);
    }
  }, [user]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header with User Info */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">LinkedIn Job Search Dashboard 🧑‍💻🔎</h1>
              <p className="text-gray-600">Find and track your dream internships and entry-level positions on LinkedIn</p>
            </div>
            
            {/* User Info & Logout */}
            {user && (
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <UserIcon className="w-4 h-4" />
                    <span>Logged in as:</span>
                  </div>
                  <div className="text-sm font-medium text-gray-900">{user.email}</div>
                  <div className="text-xs text-gray-500">ID: {user.id.slice(0, 8)}...</div>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
                >
                  <LogoutIcon className="w-4 h-4" />
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Search Configuration Panel */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Search Configuration</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            {/* Search Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Job Title Keywords</label>
              <input
                type="text"
                value={searchConfig.searchTitle}
                onChange={(e) => handleSearchConfigChange('searchTitle', e.target.value)}
                placeholder="e.g., intern, software engineer"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Location (Optional)</label>
              <input
                type="text"
                value={searchConfig.location}
                onChange={(e) => handleSearchConfigChange('location', e.target.value)}
                placeholder="e.g., San Francisco, CA"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Number of Jobs */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Number of Jobs</label>
              <select 
                value={searchConfig.numJobs}
                onChange={(e) => handleSearchConfigChange('numJobs', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value={14}>14 jobs (2 pages)</option>
                <option value={28}>28 jobs (4 pages)</option>
                <option value={56}>56 jobs (8 pages)</option>
                <option value={84}>84 jobs (12 pages)</option>
                <option value={140}>140 jobs (20 pages)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* LinkedIn Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">LinkedIn Email</label>
              <input
                type="email"
                value={searchConfig.username}
                onChange={(e) => handleSearchConfigChange('username', e.target.value)}
                placeholder="Your LinkedIn email"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* LinkedIn Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">LinkedIn Password</label>
              <input
                type="password"
                value={searchConfig.password}
                onChange={(e) => handleSearchConfigChange('password', e.target.value)}
                placeholder="Your LinkedIn password"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* User Info Display */}
          {user && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-blue-800">
                <UserIcon className="w-4 h-4" />
                <span>Jobs will be saved to your account: <strong>{user.email}</strong></span>
              </div>
            </div>
          )}

          {/* Search Button */}
          <button
            onClick={handleFetchJobs}
            disabled={isLoading || !searchConfig.username || !searchConfig.password || !user?.id}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-6 py-2 rounded-md transition-colors"
          >
            <SearchIcon className="w-4 h-4" />
            {isLoading ? 'Searching LinkedIn...' : 'Search LinkedIn Jobs'}
          </button>

          {/* Debug Info */}
          {isLoading && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="text-sm text-yellow-800">
                🔄 Scraping LinkedIn... This may take a few minutes. Check the Flask console for progress.
              </div>
            </div>
          )}
        </div>

        {/* Display both scraped jobs and saved jobs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recently Scraped Jobs */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BriefcaseIcon className="text-blue-600" />
                  <h2 className="text-lg font-semibold text-gray-900">Recently Scraped Jobs</h2>
                </div>
                <span className="text-sm text-gray-500">{jobs.length} jobs found</span>
              </div>
            </div>

            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {jobs.slice(0, 10).map((job, index) => (
                <div key={index} className="p-4 hover:bg-gray-50 transition-colors">
                  <h3 className="font-semibold text-gray-900 mb-1">{job.name}</h3>
                  <p className="text-blue-600 text-sm mb-2">{job.company}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                    <span>{job.location}</span>
                    <span>•</span>
                    <span>{job.job_type}</span>
                    {job.posting_date && (
                      <>
                        <span>•</span>
                        <span>{job.posting_date}</span>
                      </>
                    )}
                  </div>
                  {job.application_link && (
                    <a 
                      href={job.application_link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                    >
                      View Job <ExternalLinkIcon className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ))}
              {jobs.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  No jobs scraped yet. Configure search and click "Search LinkedIn Jobs".
                </div>
              )}
            </div>
          </div>

          {/* Saved Jobs from Database with Status Tracking */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BriefcaseIcon className="text-green-600" />
                  <h2 className="text-lg font-semibold text-gray-900">Your Saved Jobs</h2>
                </div>
                <span className="text-sm text-gray-500">
                  {pagination.total} jobs saved {pagination.total_pages > 1 && `(Page ${pagination.page}/${pagination.total_pages})`}
                </span>
              </div>
            </div>

            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {isLoadingUserJobs ? (
                <div className="p-8 text-center text-gray-500">
                  Loading jobs...
                </div>
              ) : userJobs.length > 0 ? (
                userJobs.map((job) => {
                  const status = job.application_status || 'not_applied';
                  const statusConfig = STATUS_CONFIG[status];
                  
                  return (
                    <div key={job.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">{job.job_name}</h3>
                          <p className="text-green-600 text-sm mb-2">{job.company}</p>
                        </div>
                        <div className="ml-4">
                          <select
                            value={status}
                            onChange={(e) => handleStatusChange(job.id, e.target.value)}
                            className={`text-xs px-2 py-1 rounded-full border-0 font-medium ${statusConfig.color} focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-green-500`}
                          >
                            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                              <option key={key} value={key}>{config.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                        <span>{job.location}</span>
                        <span>•</span>
                        <span>{job.source}</span>
                        <span>•</span>
                        <span>{new Date(job.created_at).toLocaleDateString()}</span>
                      </div>
                      
                      {job.application_link && (
                        <a 
                          href={job.application_link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-green-600 hover:text-green-800"
                        >
                          View Job <ExternalLinkIcon className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-gray-500">
                  {user ? 
                    "No saved jobs yet. Search for jobs to save them to your profile." :
                    "Please log in to view your saved jobs."
                  }
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            {pagination.total_pages > 1 && (
              <div className="p-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    Showing {((pagination.page - 1) * 50) + 1} to {Math.min(pagination.page * 50, pagination.total)} of {pagination.total} jobs
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                      className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                    >
                      <ChevronLeftIcon className="w-4 h-4" />
                      Previous
                    </button>
                    
                    <span className="text-sm text-gray-600">
                      Page {pagination.page} of {pagination.total_pages}
                    </span>
                    
                    <button
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page >= pagination.total_pages}
                      className="flex items-center gap-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-400 disabled:cursor-not-allowed"
                    >
                      Next
                      <ChevronRightIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Home