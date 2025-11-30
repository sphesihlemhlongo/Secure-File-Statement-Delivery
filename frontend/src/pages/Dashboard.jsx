import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_URL = 'https://securefilestatementdeliverybackend.vercel.app';

function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [downloadTokens, setDownloadTokens] = useState({});
  const [now, setNow] = useState(Date.now());
  const navigate = useNavigate();

  const token = localStorage.getItem('sst_token');

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    fetchDocuments();
  }, [token, navigate]);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.status === 401) {
        handleLogout();
        return;
      }
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('sst_token');
    navigate('/login');
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Upload failed');
      }

      setFile(null);
      // Reset file input
      e.target.reset();
      fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleRequestDownload = async (docId) => {
    try {
      const tokenResponse = await fetch(`${API_URL}/documents/${docId}/token`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!tokenResponse.ok) throw new Error('Failed to get download token');
      const data = await tokenResponse.json();

      // Activate download button for this document
      const expiresAt = Date.now() + (data.expires_in * 1000);
      setDownloadTokens(prev => ({
        ...prev,
        [docId]: { token: data.token, expiresAt }
      }));

    } catch (err) {
      setError(err.message);
    }
  };

  const handleDownload = (docId) => {
    const tokenData = downloadTokens[docId];
    if (tokenData && tokenData.expiresAt > now) {
      window.location.href = `${API_URL}/download?token=${tokenData.token}`;
    }
  };

  const handleCopyLink = async (docId) => {
    const tokenData = downloadTokens[docId];
    if (tokenData && tokenData.expiresAt > now) {
      const link = `${API_URL}/download?token=${tokenData.token}`;
      try {
        await navigator.clipboard.writeText(link);
        alert("Link copied to clipboard!");
      } catch (err) {
        console.error('Failed to copy:', err);
        setError('Failed to copy link to clipboard');
      }
    }
  };

  return (
    <div>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Dashboard</h1>
        <button onClick={handleLogout} className="btn-logout">Logout</button>
      </header>

      <div className="card">
        <h3>Upload New Statement</h3>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleUpload}>
          <input 
            type="file" 
            accept="application/pdf" 
            onChange={handleFileChange} 
            required 
          />
          <button type="submit" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </form>
      </div>

      <div className="card">
        <h3>Your Documents</h3>
        {documents.length === 0 ? (
          <p>No documents found.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Uploaded At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const tokenData = downloadTokens[doc.id];
                const timeLeft = tokenData ? Math.max(0, Math.ceil((tokenData.expiresAt - now) / 1000)) : 0;
                const isDownloadActive = timeLeft > 0;
                
                return (
                  <tr key={doc.id}>
                    <td>{doc.filename}</td>
                    <td>{new Date(doc.uploaded_at).toLocaleString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <button 
                          onClick={() => handleRequestDownload(doc.id)}
                          className="btn-secondary"
                        >
                          Request
                        </button>
                        <button 
                          onClick={() => handleDownload(doc.id)} 
                          disabled={!isDownloadActive}
                          style={{ 
                            opacity: isDownloadActive ? 1 : 0.5, 
                            cursor: isDownloadActive ? 'pointer' : 'not-allowed',
                            backgroundColor: isDownloadActive ? '#004c97' : '#ccc'
                          }}
                        >
                          Download {isDownloadActive ? `(${Math.floor(timeLeft / 60)}:${(timeLeft % 60).toString().padStart(2, '0')})` : ''}
                        </button>
                        <button 
                          onClick={() => handleCopyLink(doc.id)} 
                          disabled={!isDownloadActive}
                          className="btn-secondary"
                          style={{ 
                            opacity: isDownloadActive ? 1 : 0.5, 
                            cursor: isDownloadActive ? 'pointer' : 'not-allowed',
                            backgroundColor: isDownloadActive ? '#2F70EF' : '#ccc'
                          }}
                        >
                          Copy Link
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
