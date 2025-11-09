// Utility functions
function updateFileInput(input, wrapper) {
  const placeholder = wrapper.querySelector('.file-placeholder');
  const fileCount = input.files.length;
  
  if (fileCount > 0) {
    const fileName = input.files[0].name;
    wrapper.classList.add('has-file');
    placeholder.innerHTML = `
      <i class="fas fa-file-alt"></i>
      <div>Selected: <strong>${fileName}</strong></div>
      <small>Click or drag to change file</small>
    `;
  } else {
    wrapper.classList.remove('has-file');
    placeholder.innerHTML = `
      <i class="fas fa-cloud-upload-alt"></i>
      <div>Drag & drop file here</div>
      <small>or click to browse files</small>
    `;
  }
}

// Initialize file inputs
document.addEventListener('DOMContentLoaded', () => {
  // Setup file inputs
  document.querySelectorAll('.file-input').forEach(input => {
    const wrapper = input.closest('.file-input-wrapper');
    
    // Initial state
    updateFileInput(input, wrapper);

    // Handle file selection
    input.addEventListener('change', () => updateFileInput(input, wrapper));

    // Drag & drop handling
    wrapper.addEventListener('dragover', (e) => {
      e.preventDefault();
      wrapper.classList.add('dragover');
    });

    ['dragleave', 'drop'].forEach(eventName => {
      wrapper.addEventListener(eventName, (e) => {
        e.preventDefault();
        wrapper.classList.remove('dragover');
      });
    });
  });

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 300);
    }, 5000);
  });

  // Add hover animations to buttons
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('mouseenter', () => btn.style.transform = 'translateY(-2px)');
    btn.addEventListener('mouseleave', () => btn.style.transform = 'translateY(0)');
  });
});
