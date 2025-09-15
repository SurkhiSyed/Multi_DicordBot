// src/pages/Resume.jsx
import React, { useEffect, useState } from "react";
import supabase from "../helper/supabaseClient";
import { API_URL } from "../api"; // Fixed: added missing slash

const Sparkles = (props) => (
  <svg viewBox="0 0 24 24" className={props.className || "w-4 h-4"}>
    <path fill="currentColor" d="M5 3l1.5 3L10 7.5 6.5 9 5 12 3.5 9 0 7.5 3.5 6 5 3zm14 2l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2zM9 14l2 4 4 2-4 2-2 4-2-4-4-2 4-2 2-4z"/>
  </svg>
);

export default function Resume() {
  const [user, setUser] = useState(null);
  const [userJobs, setUserJobs] = useState([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);

  const [resumeFile, setResumeFile] = useState(null);
  const [useLLM, setUseLLM] = useState(false);
  const [isTuning, setIsTuning] = useState(false);

  const [result, setResult] = useState(null);
  const [activeJob, setActiveJob] = useState(null);

  const [jobDescription, setJobDescription] = useState("");
  const [projects, setProjects] = useState([""]);
  const [experiences, setExperiences] = useState([""]);
  const [skills, setSkills] = useState(""); // New state for skills

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) setUser(session.user);
    };
    init();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => {
      setUser(s?.user || null);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    (async () => {
      setIsLoadingJobs(true);
      try {
        // Replace hardcoded URL with API_URL
        const res = await fetch(`${API_URL}/api/user-jobs/${user.id}?page=1&limit=100`);
        const data = await res.json();
        if (data.success) setUserJobs(data.jobs || []);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoadingJobs(false);
      }
    })();
  }, [user]);

  useEffect(() => {
    const fetchUserInfo = async () => {
      if (!user?.id) return;

      try {
        const response = await fetch(`${API_URL}/api/user/info/${user.id}`);
        const data = await response.json();
        if (data.success) {
          setProjects(data.projects || [""]);
          setExperiences(data.experiences || [""]);
          setSkills((data.skills || []).join(", ")); // Convert skills array to a comma-separated string
        } else {
          console.error(data.error || "Failed to fetch user information");
        }
      } catch (error) {
        console.error("Error fetching user information:", error);
      }
    };

    fetchUserInfo();
  }, [user]);

  const handleTune = async (job) => {
    if (!resumeFile) {
      alert("Upload your master resume (.docx) first.");
      return;
    }
    setActiveJob(job);
    setResult(null);
    setIsTuning(true);

    try {
      const fd = new FormData();
      fd.append("file", resumeFile);
      fd.append("user_id", user.id);
      fd.append("job_description", job.description || "");
      fd.append("job_id", job.id);
      // Add optional job-specific information
      if (job.application_link) {
        fd.append("job_url", job.application_link);
      }

      const response = await fetch(`${API_URL}/api/resume/tune`, {
        method: "POST",
        body: fd,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to tune resume');
      }

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        alert(data.error || "Failed to tune resume");
      }
    } catch (error) {
      console.error("Error tuning resume:", error);
      alert(error.message || "Error tuning resume");
    } finally {
      setIsTuning(false);
    }
  };

  const handleAddProject = () => setProjects([...projects, ""]);
  const handleAddExperience = () => setExperiences([...experiences, ""]);

  const handleTuneResume = async () => {
    if (!resumeFile) {
      alert("Please upload your master resume (.docx) first.");
      return;
    }

    if (!jobDescription) {
      alert("Please enter a job description first.");
      return;
    }

    setIsTuning(true);
    setResult(null);

    try {
      const fd = new FormData();
      fd.append("file", resumeFile);
      fd.append("user_id", user.id);
      fd.append("job_description", jobDescription);
      // Add a dummy job_id for the direct tune case
      fd.append("job_id", "direct_tune");

      console.log("Sending request with:", {
        file: resumeFile.name,
        user_id: user.id,
        job_description: jobDescription.substring(0, 100) + "..."
      });

      const response = await fetch(`${API_URL}/api/resume/tune`, {
        method: "POST",
        body: fd,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to tune resume');
      }

      const data = await response.json();
      if (data.success) {
        setResult(data);
      } else {
        alert(data.error || "Failed to tune resume");
      }
    } catch (error) {
      console.error("Error tuning resume:", error);
      alert(error.message || "Error tuning resume");
    } finally {
      setIsTuning(false);
    }
  };

  const handleUpdateInformation = async () => {
    try {
      const response = await fetch(`${API_URL}/api/user/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_uuid: user.id,
          projects,
          experiences,
          skills: skills.split(",").map(skill => skill.trim()) // Convert skills to an array
        }),
      });
      const data = await response.json();
      if (data.success) {
        alert(data.message || "Information updated successfully");
      } else {
        alert(data.error || "Failed to update information");
      }
    } catch (error) {
      console.error(error);
      alert("Error updating information");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Resume Tuner ✨</h1>
            <p className="text-gray-600">Keep your format, tailor your bullets to the selected job.</p>
          </div>
          {user && (
            <div className="text-sm text-gray-600">
              {user.email} • <span className="text-gray-400">ID {user.id.slice(0,8)}…</span>
            </div>
          )}
        </header>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">1) Upload your master resume (.docx)</h2>
          <input
            type="file"
            accept=".docx,.pdf"
            onChange={(e) => {
              const file = e.target.files[0];
              console.log("Uploaded file:", file); // Debug log
              setResumeFile(file);
            }}
            className="block w-full"
          />
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useLLM}
              onChange={(e) => setUseLLM(e.target.checked)}
            />
            <span className="inline-flex items-center gap-1">
              <Sparkles /> Use local LLM via Ollama (optional)
            </span>
          </label>
          {!useLLM && (
            <p className="text-xs text-gray-500">
              No-LLM mode will still tailor bullets by weaving overlapping keywords and shortening long lines.
            </p>
          )}
        </section>

        <section className="bg-white border rounded-lg">
          <div className="p-5 flex items-center justify-between">
            <h2 className="font-semibold">2) Choose a saved job</h2>
            <div className="text-sm text-gray-500">{userJobs.length} jobs</div>
          </div>
          <div className="max-h-96 overflow-auto divide-y">
            {isLoadingJobs ? (
              <div className="p-5 text-gray-500">Loading your jobs…</div>
            ) : userJobs.length === 0 ? (
              <div className="p-5 text-gray-500">No saved jobs yet.</div>
            ) : userJobs.map(job => (
              <div key={job.id} className="p-5 flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium">{job.job_name}</div>
                  <div className="text-sm text-gray-600">{job.company}</div>
                  <div className="text-xs text-gray-500">{job.location} • {job.source}</div>
                </div>
                <button
                  onClick={() => handleTune(job)}
                  disabled={isTuning}
                  className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {isTuning && activeJob?.id === job.id ? "Tuning…" : "Tune resume for this job"}
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">1) Enter Job Description</h2>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here..."
            className="w-full border rounded p-2"
          />
        </section>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">2) Add Projects</h2>
          {projects.map((project, index) => (
            <textarea
              key={index}
              value={project}
              onChange={(e) => {
                const updatedProjects = [...projects];
                updatedProjects[index] = e.target.value;
                setProjects(updatedProjects);
              }}
              placeholder={`Project ${index + 1} description...`}
              className="w-full border rounded p-2 mb-2"
            />
          ))}
          <button onClick={handleAddProject} className="text-blue-600">
            + Add Another Project
          </button>
        </section>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">3) Add Experiences</h2>
          {experiences.map((experience, index) => (
            <textarea
              key={index}
              value={experience}
              onChange={(e) => {
                const updatedExperiences = [...experiences];
                updatedExperiences[index] = e.target.value;
                setExperiences(updatedExperiences);
              }}
              placeholder={`Experience ${index + 1} description...`}
              className="w-full border rounded p-2 mb-2"
            />
          ))}
          <button onClick={handleAddExperience} className="text-blue-600">
            + Add Another Experience
          </button>
        </section>

        <section className="bg-white border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold">4) Add Skills</h2>
          <textarea
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Enter your skills, separated by commas (e.g., Python, React, SQL)"
            className="w-full border rounded p-2"
          />
        </section>

        <button
          onClick={handleTuneResume}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Tune Resume
        </button>

        <button
          onClick={handleUpdateInformation}
          className="px-4 py-2 bg-green-600 text-white rounded"
        >
          Update Information
        </button>

        {result && (
          <section className="bg-white border rounded-lg p-5 space-y-4">
            <h2 className="font-semibold">5) Tailored Resume</h2>
            <div>
              <h3 className="font-semibold">Download Your Tailored Resume</h3>
              <a
                href={`${API_URL}${result.download_url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                Click here to download
              </a>
            </div>
            {result.change_summary && (
              <div>
                <h3 className="font-semibold">Change Summary</h3>
                <ul>
                  {result.change_summary.map((change, index) => (
                    <li key={index} className="text-gray-700">
                      - {change}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
