'use client';

import { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import AgentStatus from '@/components/AgentStatus';
import ReportViewer from '@/components/ReportViewer';

export default function IncidentDetails({ id }: { id: string }) {
    const [activeTab, setActiveTab] = useState('report');
    const [incident, setIncident] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    // Poll for updates
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`http://localhost:8000/api/v1/incidents/${id}`);
                if (res.ok) {
                    const data = await res.json();
                    setIncident(data);
                    // Stop polling if completed or failed
                    if (data.status === 'completed' || data.status === 'failed') {
                        return true; // Stop
                    }
                }
            } catch (e) {
                console.error(e);
            }
            return false; // Continue
        };

        fetchStatus().then((stop) => {
            setLoading(false);
            if (!stop) {
                const interval = setInterval(async () => {
                    const shouldStop = await fetchStatus();
                    if (shouldStop) clearInterval(interval);
                }, 1000);
                return () => clearInterval(interval);
            }
        });
    }, [id]);

    if (loading && !incident) {
        return <div className="min-h-screen bg-gray-950 text-white p-10">Loading...</div>;
    }

    if (!incident) {
        return <div className="min-h-screen bg-gray-950 text-white p-10">Incident not found</div>;
    }

    // Map backend status/step to UI steps
    // This is a simplification; ideally backend provides detailed step history.
    // We will infer steps based on the current 'step' string.

    const stepsMap = [
        { key: 'analyzing_logs', label: 'Log Analysis Agent' },
        { key: 'analyzing_metrics', label: 'Metrics Analysis Agent' },
        { key: 'inferring_root_cause', label: 'Root Cause Agent' },
        { key: 'generating_recommendations', label: 'Recommendation Agent' },
        { key: 'finalizing_report', label: 'Report Generator Agent' },
    ];

    // Very basic step progress visualization logic
    const currentStepIdx = stepsMap.findIndex(s => s.key === incident.step);
    const steps = stepsMap.map((s, idx) => {
        let status: 'pending' | 'running' | 'completed' | 'failed' = 'pending';
        if (incident.status === 'completed') status = 'completed';
        else if (incident.status === 'failed') {
            if (idx === currentStepIdx) status = 'failed';
            else if (idx < currentStepIdx) status = 'completed';
        } else {
            // processing
            if (idx < currentStepIdx) status = 'completed';
            else if (idx === currentStepIdx) status = 'running';
        }

        // If we are "done", all are completed
        if (incident.step === 'done') status = 'completed';

        return {
            name: s.label,
            status: status,
            description: status === 'running' ? 'Processing...' : status === 'completed' ? 'Done' : 'Waiting...'
        };
    });


    return (
        <div className="min-h-screen bg-gray-950 text-gray-100">
            <Navbar />
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold">Incident &nbsp;
                            <span className="text-xl font-mono text-gray-500">#{id.substring(0, 8)}</span>
                        </h1>
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${incident.status === 'completed' ? 'bg-green-900 text-green-100' :
                                incident.status === 'failed' ? 'bg-red-900 text-red-100' :
                                    'bg-yellow-900 text-yellow-100'
                            }`}>
                            {incident.status.toUpperCase()}
                        </span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left Column: Workflow Status */}
                        <div className="lg:col-span-1">
                            <AgentStatus steps={steps} />
                        </div>

                        {/* Right Column: Details & Report */}
                        <div className="lg:col-span-2">
                            <div className="bg-gray-900 shadow rounded-lg overflow-hidden min-h-[500px]">
                                <div className="border-b border-gray-800">
                                    <nav className="-mb-px flex">
                                        <button
                                            onClick={() => setActiveTab('report')}
                                            className={`${activeTab === 'report'
                                                    ? 'border-blue-500 text-blue-500'
                                                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                                                } w-1/4 py-4 px-1 text-center border-b-2 font-medium text-sm`}
                                        >
                                            Report
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('debug')}
                                            className={`${activeTab === 'debug'
                                                    ? 'border-blue-500 text-blue-500'
                                                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                                                } w-1/4 py-4 px-1 text-center border-b-2 font-medium text-sm`}
                                        >
                                            Debug info
                                        </button>
                                    </nav>
                                </div>

                                <div className="p-6">
                                    {activeTab === 'report' && (
                                        incident.result ? (
                                            <ReportViewer content={incident.result.summary} />
                                        ) : (
                                            <div className="text-gray-500 text-center mt-10">Report is generating...</div>
                                        )
                                    )}
                                    {activeTab === 'debug' && (
                                        <pre className="bg-gray-800 p-4 rounded font-mono text-xs text-green-400 whitespace-pre-wrap overflow-auto max-h-[500px]">
                                            {JSON.stringify(incident, null, 2)}
                                        </pre>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
