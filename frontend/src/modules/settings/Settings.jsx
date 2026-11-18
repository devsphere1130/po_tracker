import { useState } from 'react'
import PageHeader from '../../components/PageHeader'
import { useAuth } from '../../auth/AuthContext'
import CompanyProfile from './CompanyProfile'
import InboxIntegration from './InboxIntegration'
import OCRSettings from './OCRSettings'
import UserManagement from './UserManagement'
import RolePermissions from './RolePermissions'

export default function Settings() {
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState('company')
  const tabs = [['company', 'Company profile'], ['inbox', 'Inbox integration'], ['ocr', 'OCR'], ['roles', 'Roles & permissions'], ...(isAdmin ? [['users', 'Users']] : [])]
  return (
    <>
      <PageHeader title="Settings" subtitle="Company profile, integrations and access control" />
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'company' && <CompanyProfile />}
      {tab === 'inbox' && <InboxIntegration />}
      {tab === 'ocr' && <OCRSettings />}
      {tab === 'roles' && <RolePermissions />}
      {tab === 'users' && isAdmin && <UserManagement />}
    </>
  )
}
