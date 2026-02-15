/**
 * Sidebar Component
 *
 * Jobs history sidebar
 */

import React, { useEffect, useState } from 'react';
import { useJobStore } from '@/store/jobStore';
import { useUIStore } from '@/store/uiStore';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  const { jobs, refreshJobs, currentJobId, setCurrentJob, deleteJob } = useJobStore();
  const { setActiveTab } = useUIStore();
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);

  useEffect(() => {
    refreshJobs();
    const interval = setInterval(refreshJobs, 10000);
    return () => clearInterval(interval);
  }, [refreshJobs]);

  const jobsArray = Array.from(jobs.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const handleJobClick = (jobId: string) => {
    setCurrentJob(jobId);
    setActiveTab(0); // Navigate to Voice Replace tab
  };

  const handleDeleteClick = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation(); // Prevent job selection when clicking delete

    if (!window.confirm('Are you sure you want to delete this job?')) {
      return;
    }

    setDeletingJobId(jobId);
    try {
      await deleteJob(jobId);
    } catch (error) {
      console.error('Failed to delete job:', error);
      alert('Failed to delete job. Please try again.');
    } finally {
      setDeletingJobId(null);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <h2 className="sidebar__title">Job History</h2>
        <span className="sidebar__count">{jobsArray.length}</span>
      </div>

      <div className="sidebar__list">
        {jobsArray.length === 0 ? (
          <div className="sidebar__empty">
            <p>No jobs yet</p>
          </div>
        ) : (
          jobsArray.map((job) => (
            <div
              key={job.job_id}
              className={`sidebar__item ${currentJobId === job.job_id ? 'sidebar__item--active' : ''}`}
              onClick={() => handleJobClick(job.job_id)}
            >
              <div className="sidebar__item-header">
                <span className="sidebar__item-filename">{job.input_filename}</span>
                <div className="sidebar__item-actions">
                  <span className={`sidebar__item-status sidebar__item-status--${job.status}`}>
                    {job.status}
                  </span>
                  <button
                    className="sidebar__item-delete"
                    onClick={(e) => handleDeleteClick(e, job.job_id)}
                    disabled={deletingJobId === job.job_id}
                    title="Delete job"
                  >
                    {deletingJobId === job.job_id ? (
                      <svg className="sidebar__item-delete-spinner" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fillRule="evenodd"
                          d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
              <div className="sidebar__item-footer">
                <span className="sidebar__item-id">{job.job_id.substring(0, 8)}</span>
                <span className="sidebar__item-date">
                  {new Date(job.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
