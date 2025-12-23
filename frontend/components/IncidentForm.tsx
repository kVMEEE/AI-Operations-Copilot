'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function IncidentForm() {
    const router = useRouter();
    const [description, setDescription] = useState('');
    const [logs, setLogs] = useState('');
    const [metrics, setMetrics] = useState(''); // JSON string
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            // Parse metrics JSON
            let parsedMetrics = {};
            try {
                parsedMetrics = metrics ? JSON.parse(metrics) : {};
            } catch (e) {
                setError("Invalid JSON in Metrics field");
                setLoading(false);
                return;
            }

            const logList = logs.split('\n').filter(line => line.trim() !== '');

            const res = await fetch('http://localhost:8000/api/v1/incidents/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    description,
                    logs: logList,
                    metrics: parsedMetrics
                }),
            });

            if (!res.ok) {
                throw new Error('Failed to submit incident');
            }

            const data = await res.json();
            router.push(`/incidents/${data.job_id}`);

        } catch (err: any) {
            setError(err.message || "An error occurred");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
                <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded relative" role="alert">
                    <span className="block sm:inline">{error}</span>
                </div>
            )}
            <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-300">
                    Incident Description
                </label>
                <div className="mt-1">
                    <input
                        type="text"
                        name="description"
                        id="description"
                        required
                        className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-700 bg-gray-800 text-white rounded-md p-2"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="e.g. High latency on API"
                    />
                </div>
            </div>

            <div>
                <label htmlFor="logs" className="block text-sm font-medium text-gray-300">
                    Logs (Paste lines)
                </label>
                <div className="mt-1">
                    <textarea
                        id="logs"
                        name="logs"
                        rows={5}
                        className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-700 bg-gray-800 text-white rounded-md p-2 font-mono"
                        value={logs}
                        onChange={(e) => setLogs(e.target.value)}
                        placeholder="[ERROR] Connection timeout..."
                    />
                </div>
            </div>

            <div>
                <label htmlFor="metrics" className="block text-sm font-medium text-gray-300">
                    Metrics (JSON format)
                </label>
                <div className="mt-1">
                    <textarea
                        id="metrics"
                        name="metrics"
                        rows={5}
                        className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-700 bg-gray-800 text-white rounded-md p-2 font-mono"
                        value={metrics}
                        onChange={(e) => setMetrics(e.target.value)}
                        placeholder='{"cpu_usage": 90, "latency_ms": 1200}'
                    />
                </div>
            </div>

            <div className="flex justify-end">
                <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                    {loading ? 'Submitting...' : 'Analyze Incident'}
                </button>
            </div>
        </form>
    );
}
