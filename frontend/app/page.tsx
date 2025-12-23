'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';

interface Incident {
  job_id: string;
  status: string;
  step: string;
  result?: any;
}

export default function Home() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/incidents/')
      .then((res) => res.json())
      .then((data) => {
        setIncidents(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Navbar />
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold">Incidents</h1>
            <Link href="/incidents/new" className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
              Analyze New Incident
            </Link>
          </div>

          <div className="bg-gray-900 shadow overflow-hidden sm:rounded-md">
            {loading ? (
              <div className="p-4 text-center text-gray-400">Loading incidents...</div>
            ) : incidents.length === 0 ? (
              <div className="p-4 text-center text-gray-400">No incidents found.</div>
            ) : (
              <ul className="divide-y divide-gray-800">
                {incidents.map((incident) => (
                  <li key={incident.job_id}>
                    <Link href={`/incidents/${incident.job_id}`} className="block hover:bg-gray-800 transition duration-150 ease-in-out">
                      <div className="px-4 py-4 sm:px-6">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-blue-400 truncate">
                            Incident {incident.job_id.substring(0, 8)}...
                          </p>
                          <div className="ml-2 flex-shrink-0 flex">
                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${incident.status === 'completed' ? 'bg-green-100 text-green-800' :
                                incident.status === 'failed' ? 'bg-red-100 text-red-800' :
                                  'bg-yellow-100 text-yellow-800'
                              }`}>
                              {incident.status}
                            </span>
                          </div>
                        </div>
                        <div className="mt-2 sm:flex sm:justify-between">
                          <div className="sm:flex">
                            <p className="flex items-center text-sm text-gray-400">
                              ID: {incident.job_id}
                            </p>
                          </div>
                          <div className="mt-2 flex items-center text-sm text-gray-400 sm:mt-0">
                            <p>
                              Step: {incident.step}
                            </p>
                          </div>
                        </div>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
