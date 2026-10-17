import { useState } from 'react'
import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import FormField from '../../components/FormField.jsx'
import { useUpdateTeam } from '../../hooks/useTeams.js'

/** The team's repository. The leader and the lecturers can change it; everyone else just sees it. */
export default function RepositoryForm({ team, repoUrl, canEdit }) {
  const update = useUpdateTeam(team)
  const [value, setValue] = useState(repoUrl ?? '')
  const [error, setError] = useState('')

  if (!canEdit) {
    return (
      <Card className="p-4 text-sm">
        {repoUrl ? (
          <a href={repoUrl} target="_blank" rel="noreferrer" className="break-all text-primary hover:underline">
            {repoUrl}
          </a>
        ) : (
          <span className="text-muted-foreground">Not set yet</span>
        )}
      </Card>
    )
  }

  const save = (event) => {
    event.preventDefault()
    const url = value.trim()
    if (url && !/^https:\/\/\S+$/.test(url)) {
      setError('The address must start with https://')
      return
    }
    setError('')
    update.mutate({ repo_url: url || null })
  }

  return (
    <Card className="p-4">
      <form onSubmit={save} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <FormField label="Repository URL" error={error} className="flex-1">
          {(props) => (
            <Input
              {...props}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              placeholder="https://github.com/your-team/project"
            />
          )}
        </FormField>
        <Button type="submit" variant="outline" disabled={update.isPending || value === (repoUrl ?? '')}>
          Save
        </Button>
      </form>
    </Card>
  )
}

RepositoryForm.propTypes = {
  team: PropTypes.string.isRequired,
  repoUrl: PropTypes.string,
  canEdit: PropTypes.bool.isRequired,
}
