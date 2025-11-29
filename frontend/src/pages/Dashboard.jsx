import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_URL = 'http://localhost:8000/api';

function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  const token = localStorage.getItem('sst_token');

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

  const handleDownload = async (docId) => {
    try {
      // 1. Get Token
      const tokenResponse = await fetch(`${API_URL}/documents/${docId}/token`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!tokenResponse.ok) throw new Error('Failed to get download token');
      const tokenData = await tokenResponse.json();

      // 2. Trigger Download
      const downloadUrl = `${API_URL}/download?token=${tokenData.token}`;
      window.open(downloadUrl, '_blank');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Dashboard</h1>
        <button onClick={handleLogout} style={{ backgroundColor: '#333' }}>Logout</button>
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
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.filename}</td>
                  <td>{new Date(doc.uploaded_at).toLocaleString()}</td>
                  <td>
                    <button onClick={() => handleDownload(doc.id)}>Download</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
