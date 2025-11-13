// -------------------------
// Section Navigation
// -------------------------
function showSection(id) {
  document.querySelectorAll(".section").forEach(sec => sec.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// -------------------------
// Email Status Checking
// -------------------------
document.addEventListener('DOMContentLoaded', function() {
  // Add email status checking functionality for both main check status and history section
  const setupStatusCheck = (buttonId, inputId, resultId) => {
    const checkBtn = document.getElementById(buttonId);
    const idInput = document.getElementById(inputId);
    
    if (checkBtn && idInput) {
      checkBtn.addEventListener('click', async function() {
        const jobId = idInput.value.trim();
        if (!jobId) {
          showToast('❌ Please enter a job ID', false);
          return;
        }
        
        await checkEmailStatus(jobId, resultId, checkBtn);
      });
    }
  };
  
  // Setup main check status functionality
  const checkStatusBtn = document.getElementById('checkStatusBtn');
  const jobIdInput = document.getElementById('jobIdInput');
  
  if (checkStatusBtn && jobIdInput) {
    checkStatusBtn.addEventListener('click', async function() {
      const jobId = jobIdInput.value.trim();
      if (!jobId) {
        showToast('❌ Please enter a job ID', false);
        return;
      }
      
      await checkEmailStatus(jobId, 'statusDisplay', checkStatusBtn);
    });
  }
  
  // Setup history section status check
  setupStatusCheck('check-email-status', 'job-id-search', 'email-status-result');

  // Setup cancellation handler
  const cancelBtn = document.getElementById('cancel-email-btn');
  const cancelJobInput = document.getElementById('cancel-job-id');
  const cancelReasonInput = document.getElementById('cancel-reason');
  const cancelResult = document.getElementById('cancel-result');

  if (cancelBtn && cancelJobInput) {
    cancelBtn.addEventListener('click', async function() {
      const jobId = cancelJobInput.value.trim();
      const reason = cancelReasonInput ? cancelReasonInput.value.trim() : '';
      if (!jobId) {
        showToast('❌ Please enter a job ID to cancel', false);
        return;
      }

      const originalText = cancelBtn.textContent;
      cancelBtn.disabled = true;
      cancelBtn.innerHTML = '<span class="spinner"></span> Cancelling...';

      try {
        const res = await fetch('/cancel-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId, reason })
        });
        const data = await res.json();

        cancelBtn.disabled = false;
        cancelBtn.textContent = originalText;

        if (res.ok && data.status === 'cancelled') {
          showToast('✅ Scheduled email cancelled and recipient notified');
          addHistory(`Cancelled delivery - Job ID: ${jobId}`);
          if (cancelResult) {
            cancelResult.innerHTML = `
              <div class="status-card success">
                <h4>Cancellation</h4>
                <p><strong>Job ID:</strong> ${jobId}</p>
                <p><strong>Status:</strong> ${data.status.toUpperCase()}</p>
                <p><strong>Message:</strong> ${data.message || 'Success'}</p>
              </div>
            `;
          }
        } else {
          const msg = data.message || 'Cancellation failed';
          showToast(`❌ ${msg}`, false);
          if (cancelResult) {
            cancelResult.innerHTML = `
              <div class="status-card error">
                <h4>Cancellation Failed</h4>
                <p><strong>Job ID:</strong> ${jobId}</p>
                <p><strong>Status:</strong> ${data.status || 'error'}</p>
                <p><strong>Message:</strong> ${msg}</p>
              </div>
            `;
          }
        }
      } catch (err) {
        cancelBtn.disabled = false;
        cancelBtn.textContent = originalText;
        showToast('❌ Server error', false);
        console.error(err);
      }
    });
  }

  // -------- Dashboard population --------
  const blockCountEl = document.getElementById('blockCount');
  const recentJobsCountEl = document.getElementById('recentJobsCount');
  const pendingCountEl = document.getElementById('pendingCount');
  const recentJobsGrid = document.getElementById('recentJobsGrid');

  const renderRecentJobs = async () => {
    const jobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');
    // Update counts
    if (recentJobsCountEl) recentJobsCountEl.textContent = jobs.length;

    // Render items
    if (recentJobsGrid) {
      recentJobsGrid.innerHTML = '';
      jobs.slice(0, 5).forEach(job => {
        const item = document.createElement('div');
        item.className = 'recent-item';
        const ts = job.timestamp ? new Date(job.timestamp).toLocaleString() : 'N/A';
        item.innerHTML = `
          <div>
            <div class="file">${job.filename || 'File'}</div>
            <div class="meta">To: ${job.recipient || 'Recipient'} • ${ts}</div>
          </div>
          <div>
            <button class="mini" data-job="${job.id}">Check Status</button>
          </div>
        `;
        recentJobsGrid.appendChild(item);
      });

      // Wire status buttons
      recentJobsGrid.querySelectorAll('button.mini').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-job');
          const input = document.getElementById('job-id-search');
          if (input) input.value = id;
          showSection('history');
        });
      });
    }

    // Estimate pending by checking last few job statuses
    let pending = 0;
    const checkIds = jobs.slice(0, 5).map(j => j.id).filter(Boolean);
    await Promise.all(checkIds.map(async (id) => {
      try {
        const res = await fetch(`/email-status/${id}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'scheduled' || data.status === 'pending') pending += 1;
        }
      } catch (_) {}
    }));
    if (pendingCountEl) pendingCountEl.textContent = pending;
  };

  const renderBlockchainStats = async () => {
    try {
      const res = await fetch('/blockchain');
      if (res.ok) {
        const data = await res.json();
        if (blockCountEl) blockCountEl.textContent = data.length || 0;
      }
    } catch (err) {
      if (blockCountEl) blockCountEl.textContent = '—';
    }
  };

  renderBlockchainStats();
  renderRecentJobs();

  // -------- Upcoming deliveries --------
  const upcomingGrid = document.getElementById('upcomingGrid');
  const renderUpcoming = async () => {
    try {
      const res = await fetch('/upcoming');
      if (res.ok) {
        const data = await res.json();
        if (upcomingGrid) {
          upcomingGrid.innerHTML = '';
          const items = data.items || [];
          if (items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'recent-item';
            empty.textContent = 'No upcoming deliveries';
            upcomingGrid.appendChild(empty);
          } else {
            items.slice(0, 5).forEach(it => {
              const item = document.createElement('div');
              item.className = 'recent-item';
              const when = it.scheduled_time ? new Date(it.scheduled_time).toLocaleString() : 'N/A';
              item.innerHTML = `
                <div>
                  <div class="file">${it.subject || 'Encrypted File'}</div>
                  <div class="meta">To: ${it.recipient || 'Recipient'} • ${when}</div>
                </div>
                <div>
                  <button class="mini" data-job="${it.job_id}">Cancel</button>
                </div>
              `;
              upcomingGrid.appendChild(item);
            });
            // Wire cancel buttons to prefill
            upcomingGrid.querySelectorAll('button.mini').forEach(btn => {
              btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-job');
                const input = document.getElementById('cancel-job-id');
                if (input) input.value = id;
                showSection('history');
              });
            });
          }
        }
      }
    } catch (err) {
      console.error('Upcoming fetch error', err);
    }
  };

  renderUpcoming();

  // -------- Animated progress bars for stats --------
  const addProgressBars = () => {
    document.querySelectorAll('.stat').forEach(stat => {
      const progress = document.createElement('div');
      progress.className = 'progress';
      const bar = document.createElement('div');
      bar.className = 'bar';
      progress.appendChild(bar);
      stat.appendChild(progress);
    });
  };

  const animateBars = () => {
    const blocks = parseInt(document.getElementById('blockCount')?.textContent || '0', 10);
    const recent = parseInt(document.getElementById('recentJobsCount')?.textContent || '0', 10);
    const pending = parseInt(document.getElementById('pendingCount')?.textContent || '0', 10);

    const stats = [blocks, recent, pending];
    const max = Math.max(5, ...stats); // avoid zero
    document.querySelectorAll('.progress .bar').forEach((bar, idx) => {
      const val = stats[idx] || 0;
      const pct = Math.min(100, Math.round((val / max) * 100));
      requestAnimationFrame(() => { bar.style.width = pct + '%'; });
    });
  };

  addProgressBars();
  setTimeout(animateBars, 300);

  // -------- Theme toggle --------
  const themeToggleBtn = document.getElementById('themeToggle');
  const applyTheme = (theme) => {
    const body = document.body;
    body.classList.remove('theme-light');
    if (theme === 'light') body.classList.add('theme-light');
    localStorage.setItem('pps-theme', theme);
  };
  const currentTheme = localStorage.getItem('pps-theme') || 'dark';
  applyTheme(currentTheme);
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const next = (localStorage.getItem('pps-theme') || 'dark') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    });
  }
});

// Function to check email status
async function checkEmailStatus(jobId, resultElementId, buttonElement) {
  try {
    // Show loading state
    const originalButtonText = buttonElement.textContent;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<span class="spinner"></span> Checking...';
    
    // Fetch email status
    const response = await fetch(`/email-status/${jobId}`);
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Reset button
    buttonElement.disabled = false;
    buttonElement.textContent = originalButtonText;
    
    // Display result
    let statusText = '';
    let statusClass = '';
    
    // For debugging
    console.log('Email status data:', data);
    
    // Check if we have a valid job ID with data
    if (data.status === 'sent') {
      statusText = `✅ Email sent successfully to ${data.recipient || data.to_email || 'recipient'} at ${data.sent_time || 'unknown time'}`;
      statusClass = 'success';
      addHistory(`Email to ${data.recipient || data.to_email || 'recipient'} sent successfully - Job ID: ${jobId}`);
    } else if (data.status === 'failed') {
      statusText = `❌ Email failed to send to ${data.recipient || data.to_email || 'recipient'}. Error: ${data.error || 'Unknown error'}`;
      statusClass = 'error';
      addHistory(`Email to ${data.recipient || data.to_email || 'recipient'} failed - Job ID: ${jobId}`);
    } else if (data.status === 'pending' || data.status === 'scheduled') {
      statusText = `⏳ Email to ${data.recipient || data.to_email || 'recipient'} is scheduled for ${data.scheduled_time || data.next_run || 'future delivery'}`;
      statusClass = 'pending';
      addHistory(`Email to ${data.recipient || data.to_email || 'recipient'} is pending - Job ID: ${jobId}`);
    } else if (data.status === 'unknown') {
      // Handle unknown status with a more informative message
      statusText = `❓ ${data.message || 'No email found with this job ID'}`;
      statusClass = 'error';
      addHistory(`Email status check for Job ID: ${jobId} - Unknown status`);
    } else {
      statusText = `❓ Unknown status: ${data.status || 'No status available'}`;
      statusClass = 'error';
      addHistory(`Email status check for Job ID: ${jobId} - Unknown status`);
    }
    
    showToast(statusText, data.status === 'sent');
    
    // Update status display
    const statusDisplay = document.getElementById(resultElementId);
    if (statusDisplay) {
      // For unknown status, show a simplified error card
      if (data.status === 'unknown') {
        statusDisplay.innerHTML = `
          <div class="status-card error">
            <h4>Email Status: ${data.status.toUpperCase()}</h4>
            <p><strong>Job ID:</strong> ${jobId}</p>
            <p><strong>Message:</strong> ${data.message || 'No email found with this job ID'}</p>
          </div>
        `;
        
        // Also show a red notification at the bottom
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.innerHTML = `<span>❌ No email found with this job ID</span>`;
        document.body.appendChild(notification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
          notification.remove();
        }, 5000);
      } else {
        // Format the date/time for better readability if available
        let sentTime = data.sent_time ? new Date(data.sent_time).toLocaleString() : 'N/A';
        let scheduledTime = data.scheduled_time ? new Date(data.scheduled_time).toLocaleString() : 
                           (data.next_run ? new Date(data.next_run).toLocaleString() : 'N/A');
        
        // Create a more informative status card for valid statuses
        let statusContent = `
          <div class="status-card ${statusClass}">
            <h4>Email Status: ${data.status ? data.status.toUpperCase() : 'UNKNOWN'}</h4>
            <p><strong>Job ID:</strong> ${jobId}</p>
        `;
        
        // Only show recipient if we have one
        if (data.recipient || data.to_email) {
          statusContent += `<p><strong>Recipient:</strong> ${data.recipient || data.to_email}</p>`;
        } else {
          statusContent += `<p><strong>Recipient:</strong> N/A</p>`;
        }
        
        // Add scheduled time if available
        statusContent += `<p><strong>Scheduled:</strong> ${scheduledTime}</p>`;
        
        // Add sent time if available
        if (data.sent_time) {
          statusContent += `<p><strong>Sent:</strong> ${sentTime}</p>`;
        }
        
        // Add error message if available
        if (data.error) {
          statusContent += `<p><strong>Error:</strong> ${data.error}</p>`;
        }
        
        statusContent += `</div>`;
        
        statusDisplay.innerHTML = statusContent;
      }
      
      // Make sure the status display is visible
      statusDisplay.style.display = 'block';
    }
  } catch (error) {
    buttonElement.disabled = false;
    buttonElement.textContent = originalButtonText || 'Check Status';
    showToast(`❌ Error checking status: ${error.message}`, false);
    
    // Show error in status display as well
    const statusDisplay = document.getElementById(resultElementId);
    if (statusDisplay) {
      statusDisplay.innerHTML = `
        <div class="status-card error">
          <h4>Error</h4>
          <p>${error.message}</p>
        </div>
      `;
      statusDisplay.style.display = 'block';
    }
  }
}

// -------------------------
// Toast Notification
// -------------------------
function showToast(msg, success = true) {
  let toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  toast.style.background = success ? "rgba(0,247,255,0.9)" : "rgba(255,50,50,0.9)";
  document.body.appendChild(toast);
  setTimeout(() => { toast.remove(); }, 3500);
}

// -------------------------
// Add to History
// -------------------------
function addHistory(msg) {
  let li = document.createElement("li");
  li.textContent = msg;
  li.className = "history-item";
  document.getElementById("historyList").prepend(li);
}

// Encrypt Form
document.getElementById("encryptForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const fileInput = document.getElementById("fileInput");
  const passwordInput = document.getElementById("passwordInput");
  const emailInput = document.getElementById("emailInput");
  const dateInput = document.getElementById("dateInput");
  const timeInput = document.getElementById("timeInput");

  if (!fileInput.files[0] || !passwordInput.value || !emailInput.value || !dateInput.value || !timeInput.value) {
    showToast("❌ Please fill all fields", false);
    return;
  }

  const file = fileInput.files[0];
  const allowed = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"];
  if (!allowed.includes(file.type)) {
    showToast("❌ Unsupported file type", false);
    return;
  }

  let formData = new FormData();
  formData.append("file", file);
  formData.append("password", passwordInput.value);
  formData.append("email", emailInput.value);
  formData.append("date", dateInput.value);
  formData.append("time", timeInput.value);

  try {
    const res = await fetch("/encrypt", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      // Display job ID in the toast and history
      showToast(`✅ File encrypted & scheduled! Job ID: ${data.job_id}`);
      addHistory(`Encrypted & scheduled: "${file.name}" - Job ID: ${data.job_id}`);
      
      // Store job ID in localStorage for easy access
      const recentJobs = JSON.parse(localStorage.getItem('recentJobs') || '[]');
      recentJobs.unshift({
        id: data.job_id,
        filename: file.name,
        recipient: emailInput.value,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('recentJobs', JSON.stringify(recentJobs.slice(0, 10))); // Keep last 10 jobs
      
      this.reset();
    } else {
      showToast(data.message || "❌ Error", false);
    }
  } catch (err) {
    showToast("❌ Server error", false);
    console.error(err);
  }
});

// Decrypt Form
document.getElementById("decryptForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const fileInput = document.getElementById("decryptFile");
  const passwordInput = document.getElementById("decryptPassword");
  if (!fileInput.files[0] || !passwordInput.value) {
    showToast("❌ Select a file and enter password", false);
    return;
  }

  const file = fileInput.files[0];
  let formData = new FormData();
  formData.append("file", file);
  formData.append("password", passwordInput.value);

  try {
    const res = await fetch("/decrypt", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      // download decrypted file
      const a = document.createElement("a");
      a.href = data.download_url;
      a.download = `dec_${file.name}`;
      a.click();

      showToast("✅ File decrypted!");
      addHistory(`Decrypted: "${file.name}"`);
      this.reset();
    } else {
      showToast(data.message || "❌ Error", false);
    }
  } catch (err) {
    showToast("❌ Server error", false);
    console.error(err);
  }
});
