import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';

interface AgentStepProps {
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    description?: string;
}

export default function AgentStatus({ steps }: { steps: AgentStepProps[] }) {
    return (
        <div className="bg-gray-900 shadow overflow-hidden sm:rounded-lg mb-6">
            <div className="px-4 py-5 sm:px-6">
                <h3 className="text-lg leading-6 font-medium text-gray-100">
                    Agent Workflow Status
                </h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-400">
                    Real-time tracking of agent activities.
                </p>
            </div>
            <div className="border-t border-gray-800">
                <ul className="divide-y divide-gray-800">
                    {steps.map((step, idx) => (
                        <li key={idx} className="px-4 py-4 sm:px-6 flex items-center">
                            <div className="flex-shrink-0 mr-4">
                                {step.status === 'completed' && <CheckCircle className="h-6 w-6 text-green-500" />}
                                {step.status === 'running' && <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />}
                                {step.status === 'failed' && <XCircle className="h-6 w-6 text-red-500" />}
                                {step.status === 'pending' && <Circle className="h-6 w-6 text-gray-600" />}
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center justify-between">
                                    <p className="text-sm font-medium text-blue-400 truncate">
                                        {step.name}
                                    </p>
                                </div>
                                <div className="mt-1">
                                    <p className="flex items-center text-sm text-gray-400">
                                        {step.description || step.status}
                                    </p>
                                </div>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}
