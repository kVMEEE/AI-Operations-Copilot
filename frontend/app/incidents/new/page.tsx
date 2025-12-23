import Navbar from '@/components/Navbar';
import IncidentForm from '@/components/IncidentForm';

export default function NewIncidentPage() {
    return (
        <div className="min-h-screen bg-gray-950 text-gray-100">
            <Navbar />
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div className="px-4 py-6 sm:px-0">
                    <h1 className="text-3xl font-bold mb-6">New Incident Analysis</h1>
                    <div className="bg-gray-900 shadow sm:rounded-lg p-6">
                        <IncidentForm />
                    </div>
                </div>
            </main>
        </div>
    );
}
