#!/bin/bash

echo "Cleaning up obsolete and duplicate scripts..."

# Remove old/obsolete scripts
OBSOLETE_SCRIPTS=(
    "basedir-cleanup.py"
    "basedir-organizer.py"
    "cleanup-old-pipeline.sh"
    "convert-docker-to-k8s.sh"
    "deploy.sh"
    "direct_git_workflow.py"
    "docker-cleanup.sh"
    "docker-fix.sh"
    "docker-troubleshoot.sh"
    "final_git_workflow.py"
    "fix-argocd-config.sh"
    "fix-bugs-comprehensive.py"
    "fix-docker-issues.sh"
    "fix-docker-registry.sh"
    "fix-git-auth.sh"
    "fix-gitops-v2.sh"
    "fix-gitops.sh"
    "fix-helm-deployment.sh"
    "fix-immutable-tag.sh"
    "force-push.sh"
    "generate-argocd-app.sh"
    "generate_ppt.py"
    "git-setup.sh"
    "k8s-webhook-trigger.py"
    "kubernetes-setup.sh"
    "monitor-deployment.sh"
    "restart-docker.sh"
    "safe-deployment.sh"
    "setup-git.sh"
    "setup-k8s.sh"
    "sync-argocd.sh"
    "test-harbor.sh"
    "validate-deployment.sh"
    "verify-docker.sh"
    "verify-git-auth.sh"
    "verify-gitlab-auth.sh"
    "webhook-handler.sh"
    "webhook-listener.sh"
)

for script in "${OBSOLETE_SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        rm -f "scripts/$script"
        echo "  Removed: $script"
    fi
done

# Keep only essential scripts
echo ""
echo "Keeping essential scripts:"
ESSENTIAL_SCRIPTS=(
    "apply-pipeline-fixes.sh"
    "cleanup.sh"
    "cleanup-unused-resources.py"
    "fix-pipeline.sh"
    "validate-pipeline.sh"
    "verify_security_fixes.py"
    "analyze-pipeline-failures.py"
)

for script in "${ESSENTIAL_SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        echo "  ✓ $script"
    fi
done

echo ""
echo "Cleanup completed!"