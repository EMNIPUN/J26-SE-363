import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '../../auth/useAuth.js'
import PictureField from '../../components/PictureField.jsx'
import Badge from '../../components/Badge.jsx'
import { getRoleLabel } from '../../constants/roles.js'
import { accountService } from '../../services/accountService.js'
import { isGithubUsername } from '../../utils/emails.js'
import { showToast } from '../../utils/toast.jsx'
import FormField from '../../components/FormField.jsx'
import PageHeader from '../../components/PageHeader.jsx'

const text = (value) => value ?? ''

export default function ProfilePage() {
  const { account, user, setAccount } = useAuth()
  const isStudent = user.role === 'student'
  const isAdmin = user.role === 'admin'
  const [values, setValues] = useState({
    displayName: text(account.name),
    institution: text(account.profile.institution),
    githubUsername: text(account.profile.github_username),
    studentNumber: text(account.profile.student_number),
    department: text(account.profile.department),
    title: text(account.profile.title),
  })
  const [errors, setErrors] = useState({})

  const upload = useMutation({
    mutationFn: accountService.uploadPicture,
    onSuccess: (updated) => {
      setAccount(updated)
      showToast.success('Picture updated')
    },
    onError: (error) => showToast.error(error.message),
  })
  const remove = useMutation({
    mutationFn: accountService.removePicture,
    onSuccess: (updated) => {
      setAccount(updated)
      showToast.success('Picture removed')
    },
    onError: (error) => showToast.error(error.message),
  })

  const save = useMutation({
    mutationFn: accountService.updateProfile,
    onSuccess: (updated) => {
      setAccount(updated)
      showToast.success('Profile saved')
    },
    onError: (error) => {
      if (error.code === 'github_username_taken') setErrors({ githubUsername: error.message })
      else if (error.code === 'student_number_taken') setErrors({ studentNumber: error.message })
      else showToast.error(error.message)
    },
  })

  const field = (name) => ({
    value: values[name],
    onChange: (event) => {
      setValues((current) => ({ ...current, [name]: event.target.value }))
      setErrors((current) => ({ ...current, [name]: undefined }))
    },
  })

  const submit = (event) => {
    event.preventDefault()
    const found = {}
    if (!values.displayName.trim()) found.displayName = 'Enter your name.'
    if (isStudent && !isGithubUsername(values.githubUsername)) {
      found.githubUsername = 'Enter a valid GitHub username.'
    }
    setErrors(found)
    if (Object.keys(found).length) return
    save.mutate({
      display_name: values.displayName,
      institution: values.institution,
      ...(isStudent
        ? { github_username: values.githubUsername, student_number: values.studentNumber }
        : { department: values.department, title: values.title }),
    })
  }

  return (
    <div className="grid gap-6">
      <PageHeader title="Profile" description="How you appear to your team and lecturers." />

      <Card className="flex-col items-start gap-4 p-5 sm:flex-row sm:items-center">
        <PictureField
          name={account.name}
          picture={account.picture}
          size={64}
          loading={upload.isPending}
          onPick={upload.mutateAsync}
          // only an upload can be removed; the provider's picture comes back by itself
          onRemove={account.picture?.startsWith('/') ? () => remove.mutate() : undefined}
        />
        <div className="min-w-0 border-l border-border pl-4">
          <p className="truncate text-base font-semibold text-foreground">{account.name}</p>
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="truncate">{account.email}</span>
            {account.email_verified && <Badge tone="success">Verified</Badge>}
          </p>
        </div>
        <Badge tone="primary" className="shrink-0 sm:ml-auto">
          {getRoleLabel(user.role)}
        </Badge>
      </Card>

      <Card className="p-5 sm:p-6">
        <form onSubmit={submit} className="grid gap-4">
          {isAdmin ? (
            <p className="text-sm text-muted-foreground">
              Administrator details are managed in Keycloak.
            </p>
          ) : (
            <>
              <FormField label="Full name" error={errors.displayName}>
                {(props) => <Input {...props} {...field('displayName')} autoComplete="name" />}
              </FormField>
              <FormField label="Institution" optional>
                {(props) => <Input {...props} {...field('institution')} />}
              </FormField>
              {isStudent ? (
                <>
                  <FormField label="GitHub username" error={errors.githubUsername}>
                    {(props) => <Input {...props} {...field('githubUsername')} />}
                  </FormField>
                  <FormField label="Student number" optional error={errors.studentNumber}>
                    {(props) => <Input {...props} {...field('studentNumber')} />}
                  </FormField>
                </>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField label="Department" optional>
                    {(props) => <Input {...props} {...field('department')} />}
                  </FormField>
                  <FormField label="Title" optional>
                    {(props) => <Input {...props} {...field('title')} />}
                  </FormField>
                </div>
              )}
              <div className="flex justify-end">
                <Button type="submit" loading={save.isPending}>
                  Save changes
                </Button>
              </div>
            </>
          )}
        </form>
      </Card>
    </div>
  )
}
