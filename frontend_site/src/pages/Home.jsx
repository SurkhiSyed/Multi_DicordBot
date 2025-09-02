// src/pages/Home.jsx
import React, { useState, useEffect, useMemo } from 'react';
import supabase from '../helper/supabaseClient';

// Icons (unchanged)
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
  not_applied: { label: 'Not Applied', color: 'bg-gray-100 text-gray-800' },
  applied: { label: 'Applied', color: 'bg-blue-100 text-blue-800' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800' },
  interview: { label: 'Interview', color: 'bg-yellow-100 text-yellow-800' },
  offer: { label: 'Offer', color: 'bg-green-100 text-green-800' }
};

// small helpers
const truncate = (text = '', max = 260) =>
  text.length > max ? text.slice(0, max).trim() + '…' : text;

const badge = (label) => (
  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-gray-100 text-gray-700">
    {label}
  </span>
);

function Home() {
  const [jobs, setJobs] = useState([]);                 // scraped jobs (from /api/jobs)
  const [userJobs, setUserJobs] = useState([]);         // saved jobs (from DB)
  const [pagination, setPagination] = useState({ page: 1, total: 0, total_pages: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingUserJobs, setIsLoadingUserJobs] = useState(false);
  const [user, setUser] = useState(null);

  // track expanded descriptions (recent & saved)
  const [expandedScraped, setExpandedScraped] = useState(() => new Set());
  const [expandedSaved, setExpandedSaved] = useState(() => new Set());

  const [searchConfig, setSearchConfig] = useState({
    username: '',
    password: '',
    numJobs: 56,
    searchTitle: 'intern',
    location: ''
  });

  // session
  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) setUser(session.user);
    };
    init();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_evt, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (user?.id) fetchUserJobs(1);
  }, [user]);

  const handleSearchConfigChange = (field, value) => {
    setSearchConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.error('Error logging out:', err);
    }
  };

  const handleStatusChange = async (jobId, newStatus) => {
    if (!user?.id) return;
    try {
      const res = await fetch(`http://localhost:8000/api/user-jobs/${user.id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, status: newStatus })
      });
      const data = await res.json();
      if (!data.success) {
        alert(`Failed to update status: ${data.error}`);
        return;
      }
      setUserJobs(prev =>
        prev.map(j => (j.id === jobId ? { ...j, application_status: newStatus } : j))
      );
    } catch (err) {
      console.error('❌ Error updating job status:', err);
      alert('Failed to update job status');
    }
  };

  const handleFetchJobs = async () => {
    if (!user?.id) {
      alert('User session not found. Please log out and in again.');
      return;
    }
    if (!searchConfig.username || !searchConfig.password) {
      alert('Please enter your LinkedIn credentials');
      return;
    }

    setIsLoading(true);
    setExpandedScraped(new Set()); // reset expands for fresh results

    try {
      const body = {
        linkedin_username: searchConfig.username,
        linkedin_password: searchConfig.password,
        num_jobs: searchConfig.numJobs,
        searchTitle: searchConfig.searchTitle,
        location: searchConfig.location,
        user_id: user.id,
      };

      const res = await fetch(`http://localhost:8000/api/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        console.error('❌ API error:', data?.error || res.statusText);
        alert(`Error: ${data?.error || 'Failed to fetch jobs'}`);
        return;
      }

      setJobs(Array.isArray(data.jobs) ? data.jobs : []);
      if (data.database) {
        alert(
          `Scraping completed!
Found: ${data.total_jobs} new jobs
Saved to DB: ${data.database.saved}
Duplicates skipped: ${data.database.duplicates}`
        );
      }
      await fetchUserJobs(1);
    } catch (err) {
      console.error('❌ Error fetching jobs:', err);
      alert(`Failed to fetch jobs: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserJobs = async (page = 1) => {
    if (!user?.id) return;
    setIsLoadingUserJobs(true);
    setExpandedSaved(new Set()); // reset expands when page changes

    try {
      const res = await fetch(
        `http://localhost:8000/api/user-jobs/${user.id}?page=${page}&limit=50`
      );
      const data = await res.json();
      if (data.success) {
        setUserJobs(Array.isArray(data.jobs) ? data.jobs : []);
        setPagination(data.pagination || { page, total: 0, total_pages: 0 });
      } else {
        console.error('❌ Failed to fetch user jobs:', data.error);
      }
    } catch (err) {
      console.error('❌ Error fetching user jobs:', err);
    } finally {
      setIsLoadingUserJobs(false);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= (pagination.total_pages || 1)) {
      fetchUserJobs(newPage);
    }
  };

  const toggleExpandedScraped = (idx) => {
    setExpandedScraped(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const toggleExpandedSaved = (id) => {
    setExpandedSaved(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const scrapedCount = useMemo(() => jobs.length || 0, [jobs]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                LinkedIn Job Search Dashboard 🧑‍💻🔎
              </h1>
              <p className="text-gray-600">
                Find and track your internships and entry-level roles from LinkedIn
              </p>
            </div>

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
                  <LogoutIcon className="w-4 h-4"/>
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Search Configuration */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Search Configuration</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Location (Optional)</label>
              <input
                type="text"
                value={searchConfig.location}
                onChange={(e) => handleSearchConfigChange('location', e.target.value)}
                placeholder="e.g., Toronto, ON"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

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

          {user && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-blue-800">
                <UserIcon className="w-4 h-4" />
                <span>Jobs will be saved to your account: <strong>{user.email}</strong></span>
              </div>
            </div>
          )}

          <button
            onClick={handleFetchJobs}
            disabled={isLoading || !searchConfig.username || !searchConfig.password || !user?.id}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium px-6 py-2 rounded-md transition-colors"
          >
            <SearchIcon className="w-4 h-4" />
            {isLoading ? 'Searching LinkedIn...' : 'Search LinkedIn Jobs'}
          </button>

          {isLoading && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
              🔄 Scraping LinkedIn… check the Flask console for progress.
            </div>
          )}
        </div>

        {/* Two columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recently Scraped Jobs */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BriefcaseIcon className="text-blue-600" />
                  <h2 className="text-lg font-semibold text-gray-900">Recently Scraped Jobs</h2>
                </div>
                <span className="text-sm text-gray-500">{scrapedCount} jobs found</span>
              </div>
            </div>

            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {jobs.length > 0 ? (
                jobs.map((job, index) => {
                  const expanded = expandedScraped.has(index);
                  const desc = job?.description || '';
                  const hasDesc = Boolean(desc && desc.trim().length);

                  return (
                    <div key={`${job.application_link || index}-${index}`} className="p-4 hover:bg-gray-50 transition-colors">
                      <h3 className="font-semibold text-gray-900 mb-1">{job.name}</h3>
                      <p className="text-blue-600 text-sm mb-2">{job.company || '—'}</p>

                      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 mb-2">
                        {job.location && <span>{job.location}</span>}
                        {job.job_type && <>• <span>{badge(job.job_type)}</span></>}
                        {job.location_type && <>• <span>{badge(job.location_type)}</span></>}
                        {job.posting_date && <>• <span>{job.posting_date}</span></>}
                      </div>

                      {hasDesc && (
                        <div className="text-sm text-gray-700 mb-2">
                          {expanded ? desc : truncate(desc)}
                          {desc.length > 260 && (
                            <button
                              onClick={() => toggleExpandedScraped(index)}
                              className="ml-2 text-blue-600 hover:text-blue-800 text-xs font-medium"
                            >
                              {expanded ? 'Show less' : 'Show more'}
                            </button>
                          )}
                        </div>
                      )}

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
                  );
                })
              ) : (
                <div className="p-8 text-center text-gray-500">
                  No jobs scraped yet. Configure search and click “Search LinkedIn Jobs”.
                </div>
              )}
            </div>
          </div>

          {/* Saved Jobs */}
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
                <div className="p-8 text-center text-gray-500">Loading jobs…</div>
              ) : userJobs.length > 0 ? (
                userJobs.map(job => {
                  const statusKey = job.application_status || 'not_applied';
                  const statusCfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.not_applied;
                  const expanded = expandedSaved.has(job.id);
                  const desc = job?.description || '';
                  const hasDesc = Boolean(desc && desc.trim().length);

                  return (
                    <div key={job.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">{job.job_name}</h3>
                          <p className="text-green-600 text-sm mb-2">{job.company || '—'}</p>
                        </div>
                        <div className="ml-4">
                          <select
                            value={statusKey}
                            onChange={(e) => handleStatusChange(job.id, e.target.value)}
                            className={`text-xs px-2 py-1 rounded-full border-0 font-medium ${statusCfg.color} focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-green-500`}
                          >
                            {Object.entries(STATUS_CONFIG).map(([k, cfg]) => (
                              <option key={k} value={k}>{cfg.label}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 mb-2">
                        {job.location && <span>{job.location}</span>}
                        {job.job_type && <>• <span>{badge(job.job_type)}</span></>}
                        {job.location_type && <>• <span>{badge(job.location_type)}</span></>}
                        {job.source && <>• <span>{job.source}</span></>}
                        {job.created_at && <>• <span>{new Date(job.created_at).toLocaleDateString()}</span></>}
                      </div>

                      {hasDesc && (
                        <div className="text-sm text-gray-700 mb-2">
                          {expanded ? desc : truncate(desc)}
                          {desc.length > 260 && (
                            <button
                              onClick={() => toggleExpandedSaved(job.id)}
                              className="ml-2 text-green-600 hover:text-green-800 text-xs font-medium"
                            >
                              {expanded ? 'Show less' : 'Show more'}
                            </button>
                          )}
                        </div>
                      )}

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
                  {user ? "No saved jobs yet. Search to populate your list." : "Please log in to view your saved jobs."}
                </div>
              )}
            </div>

            {/* Pagination */}
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
  );
}

export default Home;
