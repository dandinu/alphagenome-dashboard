import { Link, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  Home,
  Database,
  FileSearch,
  Microscope,
  Pill,
  AlertTriangle,
  Settings,
  Dna,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Load Data', href: '/files', icon: Database },
  { name: 'Variant Explorer', href: '/variants', icon: FileSearch },
  { name: 'Analysis', href: '/analysis', icon: Microscope },
  { name: 'Pharmacogenomics', href: '/pharmacogenomics', icon: Pill },
  { name: 'Disease Risk', href: '/disease-risk', icon: AlertTriangle },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex h-screen w-64 flex-col bg-gray-900">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-6 border-b border-gray-800">
        <Dna className="h-8 w-8 text-primary-400" />
        <div>
          <h1 className="text-lg font-semibold text-white">AlphaGenome</h1>
          <p className="text-xs text-gray-400">Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800 p-4">
        <div className="rounded-lg bg-gray-800 p-3">
          <p className="text-xs text-gray-400">Powered by</p>
          <p className="text-sm font-medium text-white">Google DeepMind</p>
          <p className="text-xs text-gray-500">AlphaGenome API</p>
        </div>
      </div>
    </div>
  );
}
