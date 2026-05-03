import { Upload, Settings as SettingsIcon, Server, Shield } from 'lucide-react'
import FileUploadSection from './FileUploadSection'
import { Card, CardBody, CardHeader } from './Card'
import { Button } from './Button'
import { Badge } from './Badge'

export default function SettingsPanel() {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#ead8b0] bg-[#fff4dc] px-3 py-1 text-sm text-amber-800 dark:border-[#24406e] dark:bg-[#13213f] dark:text-blue-100">
            <SettingsIcon className="h-4 w-4" />
            Workspace settings
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
          <p className="max-w-2xl text-gray-600 dark:text-blue-100/75">
            Manage document ingestion, indexing status, and future workspace preferences from one place.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <Card className="bg-[#fbf6ec] dark:bg-[#10192c] border-[#e0d3c1] dark:border-[#22314f]">
            <CardHeader className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-blue-200">Document ingestion</p>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Upload documents</h2>
              </div>
              <Badge variant="info">Primary workflow</Badge>
            </CardHeader>
            <CardBody className="p-0">
              <FileUploadSection />
            </CardBody>
          </Card>

          <div className="space-y-6">
            <Card className="bg-[#fbf6ec] dark:bg-[#10192c] border-[#e0d3c1] dark:border-[#22314f]">
              <CardHeader>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Indexing status</h2>
              </CardHeader>
              <CardBody className="space-y-4">
                <div className="flex items-center gap-3 rounded-lg border border-[#eadcbf] bg-[#fff6e2] p-4 dark:border-[#24406e] dark:bg-[#13213f]">
                  <Server className="h-5 w-5 text-amber-700 dark:text-blue-300" />
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">Vector store</p>
                    <p className="text-sm text-gray-600 dark:text-blue-100/70">Ready for document ingestion</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 rounded-lg border border-[#eadcbf] bg-[#fff6e2] p-4 dark:border-[#24406e] dark:bg-[#13213f]">
                  <Shield className="h-5 w-5 text-amber-700 dark:text-blue-300" />
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">Access controls</p>
                    <p className="text-sm text-gray-600 dark:text-blue-100/70">Reserved for future settings</p>
                  </div>
                </div>
              </CardBody>
            </Card>

            <Card className="bg-[#fbf6ec] dark:bg-[#10192c] border-[#e0d3c1] dark:border-[#22314f]">
              <CardHeader>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Quick actions</h2>
              </CardHeader>
              <CardBody className="space-y-3">
                <Button variant="primary" className="w-full justify-center">
                  <Upload className="h-4 w-4" />
                  Add more documents
                </Button>
                <Button variant="outline" className="w-full justify-center">
                  View upload guidance
                </Button>
              </CardBody>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
