import IncidentDetails from './IncidentDetails';

export async function generateStaticParams() {
    return [{ id: '1' }, { id: '2' }];
}

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    return <IncidentDetails id={id} />;
}
