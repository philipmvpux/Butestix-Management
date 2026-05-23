import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { name, company, email } = req.body;

    // Validation
    if (!name || !company || !email) {
      return res.status(400).json({ status: 'error', message: 'Missing fields' });
    }

    // Create applicant data
    const data = {
      name,
      company,
      email,
      timestamp: new Date().toISOString()
    };

    // Log to console (Vercel shows this in logs)
    console.log('✅ Neue Anfrage:', data);

    // Response
    return res.status(200).json({ status: 'success' });
  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({ status: 'error', message: error.message });
  }
}
