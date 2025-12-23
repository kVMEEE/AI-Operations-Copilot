import ReactMarkdown from 'react-markdown';

export default function ReportViewer({ content }: { content: string }) {
    return (
        <div className="prose prose-invert max-w-none bg-gray-900 p-6 rounded-lg shadow">
            <ReactMarkdown>{content}</ReactMarkdown>
        </div>
    );
}
