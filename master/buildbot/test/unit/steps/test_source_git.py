# This file is part of Buildbot.  Buildbot is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Buildbot Team Members

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from parameterized import parameterized
from twisted.internet import defer
from twisted.internet import error
from twisted.trial import unittest

from buildbot import config as bbconfig
from buildbot.interfaces import WorkerSetupError
from buildbot.process import buildstep
from buildbot.process import remotetransfer
from buildbot.process.properties import Interpolate
from buildbot.process.results import EXCEPTION
from buildbot.process.results import FAILURE
from buildbot.process.results import RETRY
from buildbot.process.results import SUCCESS
from buildbot.steps.source import git
from buildbot.test.reactor import TestReactorMixin
from buildbot.test.steps import ExpectCpdir
from buildbot.test.steps import ExpectDownloadFile
from buildbot.test.steps import ExpectListdir
from buildbot.test.steps import ExpectMkdir
from buildbot.test.steps import ExpectRemoteRef
from buildbot.test.steps import ExpectRmdir
from buildbot.test.steps import ExpectShell
from buildbot.test.steps import ExpectStat
from buildbot.test.steps import TestBuildStepMixin
from buildbot.test.util import config
from buildbot.test.util import sourcesteps
from buildbot.util import unicode2bytes
from buildbot.util.git_credential import GitCredentialOptions

if TYPE_CHECKING:
    from buildbot.util.twisted import InlineCallbacksType


class TestGit(
    sourcesteps.SourceStepMixin, config.ConfigErrorsMixin, TestReactorMixin, unittest.TestCase
):
    stepClass = git.Git

    def setUp(self) -> defer.Deferred[None]:  # type: ignore[override]
        self.setup_test_reactor()
        self.sourceName = self.stepClass.__name__
        return self.setup_test_build_step()

    def test_mode_full_filters_2_26(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                filters=['tree:0'],
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.26.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_filters_2_27(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                filters=['tree:0'],
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.27.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--filter',
                    'tree:0',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_clean_filters_existing_repo_2_26(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                filters=['tree:0'],
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.26.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_fresh_filters_existing_repo_2_27(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                filters=['blob:limit=1m', 'tree:0'],
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.27.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.origin.promisor'],
            ).exit(1),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.origin.partialclonefilter'],
            ).exit(1),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', 'remote.origin.promisor', 'true'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'config',
                    'remote.origin.partialclonefilter',
                    'combine:blob:limit=1m+tree:0',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--filter',
                    'blob:limit=1m',
                    '--filter',
                    'tree:0',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_incremental_filters_existing_repo_already_configured_2_27(
        self,
    ) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                filters=['tree:0'],
                origin='upstream',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.27.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.upstream.promisor'],
            )
            .stdout('true')
            .exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.upstream.partialclonefilter'],
            )
            .stdout('tree:0')
            .exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--filter',
                    'tree:0',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_incremental_filters_existing_repo_changed_filter_2_27(
        self,
    ) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                filters=['tree:0'],
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.27.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.origin.promisor'],
            )
            .stdout('true')
            .exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', '--get', 'remote.origin.partialclonefilter'],
            )
            .stdout('blob:none')
            .exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', 'remote.origin.promisor', 'true'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'config', 'remote.origin.partialclonefilter', 'tree:0'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--filter',
                    'tree:0',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    @parameterized.expand([
        ('promisor_write', 0),
        ('filter_write', 1),
    ])
    @defer.inlineCallbacks
    def test_partial_clone_config_write_failure(
        self, name: str, failing_write: int
    ) -> InlineCallbacksType[None]:
        step = self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                filters=['blob:none'],
            )
        )
        object.__setattr__(step, 'supportsFilters', True)
        writes: list[list[str]] = []

        def fake_dovccmd(command: list[str], **kwargs: Any) -> defer.Deferred[str | int]:
            if '--get' in command:
                return defer.succeed('')
            write_number = len(writes)
            writes.append(command)
            return defer.succeed(FAILURE if write_number == failing_write else SUCCESS)

        self.patch(step, '_dovccmd', fake_dovccmd)

        yield self.assertFailure(step._ensurePartialCloneConfig(), buildstep.BuildStepFailed)
        self.assertEqual(len(writes), failing_write + 1)

    @parameterized.expand([
        ('equals_unescaped', 'blob:limit=1m', 'blob:limit=1m'),
        ('plus', 'sparse:oid=foo+bar', 'sparse:oid=foo%2Bbar'),
        ('percent', 'sparse:oid=foo%bar', 'sparse:oid=foo%25bar'),
        ('space', 'sparse:oid=foo bar', 'sparse:oid=foo%20bar'),
        ('reserved', 'sparse:oid=foo?bar', 'sparse:oid=foo%3Fbar'),
    ])
    def test_encode_filter_for_combine(self, name: str, filter: str, encoded_filter: str) -> None:
        step = self.stepClass(repourl='http://github.com/buildbot/buildbot.git')

        self.assertEqual(step._encodeFilterForCombine(filter), encoded_filter)

    @parameterized.expand([
        ('url', 'ssh://github.com/test/test.git', 'ssh://github.com/test/test.git'),
        (
            'url_renderable',
            Interpolate('ssh://github.com/test/test.git'),
            'ssh://github.com/test/test.git',
        ),
        ('ssh_host_and_path', 'host:path/to/git', 'ssh://host:22/path/to/git'),
        (
            'ssh_host_and_path_renderable',
            Interpolate('host:path/to/git'),
            'ssh://host:22/path/to/git',
        ),
    ])
    def test_mode_full_clean(
        self, name: str, url: str | Interpolate, pull_url: str
    ) -> defer.Deferred[None]:
        self.setup_step(self.stepClass(repourl=url, mode='full', method='clean'))
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    pull_url,
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_failure_clobbers_when_configured(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                clobberOnFailure=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_progress_False(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                progress=False,
                tags=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--tags',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_ssh_key_2_10(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_command_config = f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_ssh_key_2_3(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_command = f'ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.3.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    @defer.inlineCallbacks
    def test_mode_full_clean_ssh_key_1_7(self) -> InlineCallbacksType[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_wrapper_path = '/wrk/.bldr.wkdir.buildbot/ssh-wrapper.sh'

        # A place to store what gets read
        read = []  # type: ignore[var-annotated]

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            )
            .download_string(read.append)
            .exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        yield self.run_step()

        expected = f'#!/bin/sh\nssh -o "BatchMode=yes" -i "{ssh_key_path}" "$@"\n'
        self.assertEqual(b''.join(read), unicode2bytes(expected))

    @parameterized.expand([
        ('host_key', {"sshHostKey": 'sshhostkey'}),
        ('known_hosts', {"sshKnownHosts": 'known_hosts'}),
    ])
    def test_mode_full_clean_ssh_host_key_2_10(
        self, name: str, class_params: dict[str, Any]
    ) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
                **class_params,
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'
        ssh_command_config = (
            f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}" '
            f'-o "UserKnownHostsFile={ssh_known_hosts_path}"'
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_ssh_host_key_2_3(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'
        ssh_command = (
            f'ssh -o "BatchMode=yes" -i "{ssh_key_path}" '
            f'-o "UserKnownHostsFile={ssh_known_hosts_path}"'
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.3.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    @defer.inlineCallbacks
    def test_mode_full_clean_ssh_host_key_1_7(self) -> InlineCallbacksType[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
                tags=True,
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_wrapper_path = '/wrk/.bldr.wkdir.buildbot/ssh-wrapper.sh'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'

        # A place to store what gets read
        read = []  # type: ignore[var-annotated]

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            )
            .download_string(read.append)
            .exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--tags',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        yield self.run_step()

        expected = (
            '#!/bin/sh\n'
            f'ssh -o "BatchMode=yes" -i "{ssh_key_path}" -o '
            f'"UserKnownHostsFile={ssh_known_hosts_path}" "$@"\n'
        )
        self.assertEqual(b''.join(read), unicode2bytes(expected))

    def test_mode_full_clean_ssh_host_key_1_7_progress(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
                progress=True,
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_wrapper_path = '/wrk/.bldr.wkdir.buildbot/ssh-wrapper.sh'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_ssh_host_key_2_10_abs_workdir(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
            ),
            want_default_work_dir=False,
        )
        workdir = '/myworkdir/workdir'
        self.build.workdir = workdir

        ssh_workdir = '/myworkdir/.bldr.workdir.buildbot'
        ssh_key_path = '/myworkdir/.bldr.workdir.buildbot/ssh-key'
        ssh_known_hosts_path = '/myworkdir/.bldr.workdir.buildbot/ssh-known-hosts'
        ssh_command_config = (
            f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}" '
            f'-o "UserKnownHostsFile={ssh_known_hosts_path}"'
        )

        self.expect_commands(
            ExpectShell(workdir=workdir, command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='/myworkdir/workdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir=workdir).files(['.git']).exit(0),
            ExpectShell(workdir=workdir, command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir=workdir,
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir=workdir,
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir=workdir, command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_win32path(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            )
        )
        self.change_worker_system('nt')
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file=r'wkdir\.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_win32path_ssh_key_2_10(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )
        self.change_worker_system('nt')

        ssh_workdir = '\\wrk\\.bldr.wkdir.buildbot'
        ssh_key_path = '\\wrk\\.bldr.wkdir.buildbot\\ssh-key'
        ssh_command_config = f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir\\.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_win32path_ssh_key_2_3(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )
        self.change_worker_system('nt')

        ssh_workdir = '\\wrk\\.bldr.wkdir.buildbot'
        ssh_key_path = '\\wrk\\.bldr.wkdir.buildbot\\ssh-key'
        ssh_command = f'ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.3.0')
            .exit(0),
            ExpectStat(file='wkdir\\.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_win32path_ssh_key_1_7(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                sshPrivateKey='sshkey',
            )
        )
        self.change_worker_system('nt')

        ssh_workdir = '\\wrk\\.bldr.wkdir.buildbot'
        ssh_key_path = '\\wrk\\.bldr.wkdir.buildbot\\ssh-key'
        ssh_wrapper_path = '\\wrk\\.bldr.wkdir.buildbot\\ssh-wrapper.sh'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectStat(file='wkdir\\.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_timeout(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                timeout=1,
                mode='full',
                method='clean',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', timeout=1, command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir', timeout=1, command=['git', 'clean', '-f', '-f', '-d']
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                timeout=1,
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir', timeout=1, command=['git', 'checkout', '-f', 'FETCH_HEAD']
            ).exit(0),
            ExpectShell(workdir='wkdir', timeout=1, command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_patch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            ),
            patch=(1, 'patch'),
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x'], log_environ=True
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest='.buildbot-diff',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest='.buildbot-patched',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'update-index', '--refresh']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'apply', '--index', '-p', '1'],
                initial_stdin='patch',
            ).exit(0),
            ExpectRmdir(dir='wkdir/.buildbot-diff', log_environ=True).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_patch_worker_2_16(self) -> defer.Deferred[None]:
        self.setup_build(worker_version={'*': '2.16'})
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            ),
            patch=(1, 'patch'),
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x'], log_environ=True
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                slavedest='.buildbot-diff',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                slavedest='.buildbot-patched',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'update-index', '--refresh']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'apply', '--index', '-p', '1'],
                initial_stdin='patch',
            ).exit(0),
            ExpectRmdir(dir='wkdir/.buildbot-diff', log_environ=True).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_patch_fail(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            ),
            patch=(1, 'patch'),
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest='.buildbot-diff',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest='.buildbot-patched',
                workdir='wkdir',
                mode=None,
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'update-index', '--refresh']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'apply', '--index', '-p', '1'],
                initial_stdin='patch',
            ).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        self.expect_no_property('got_revision')
        return self.run_step()

    def test_mode_full_clean_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                branch='test-branch',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-B', 'test-branch']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_tags(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                tags=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--tags',
                    "--progress",
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_non_empty_builddir(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                branch='test-branch',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['file1', 'file2']).exit(0),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--branch',
                    'test-branch',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_parsefail(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD'])
            .stderr("fatal: Could not parse object 'b08076bc71c7813038f2cefedff9c5b678d225a8'.\n")
            .exit(128),
        )
        self.expect_outcome(result=FAILURE)
        self.expect_no_property('got_revision')
        return self.run_step()

    def test_mode_full_clean_no_existing_repo(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_clean_no_existing_repo_with_reference(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                reference='path/to/reference/repo',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--reference',
                    'path/to/reference/repo',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_clean_no_existing_repo_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                branch='test-branch',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--branch',
                    'test-branch',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_clean_no_existing_repo_with_origin(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                origin='foo',
                progress=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--origin',
                    'foo',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_clean_submodule(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                submodules=True,
                progress=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'foreach', '--recursive', 'git clean -f -f -d'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_submodule_remotes(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clean',
                submodules=True,
                progress=True,
                remoteSubmodules=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'update', '--init', '--recursive', '--remote'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'foreach', '--recursive', 'git clean -f -f -d'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_submodule_remotes(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                submodules=True,
                progress=True,
                remoteSubmodules=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'update', '--init', '--recursive', '--remote'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clone_fails(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(1),  # clone fails
        )
        self.expect_outcome(result=FAILURE, state_string="update (failure)")
        self.expect_no_property('got_revision')
        return self.run_step()

    def test_mode_full_clobber_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
                branch='test-branch',
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--branch',
                    'test-branch',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_no_branch_support_shallow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                branch='test-branch',
                shallow=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.5.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--depth',
                    '1',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--depth',
                    '1',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-B', 'test-branch']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_no_branch_support(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                branch='test-branch',
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.5.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'clone', 'http://github.com/buildbot/buildbot.git', '.'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-B', 'test-branch']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_oldworker(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='incremental', progress=True
            )
        )
        self.get_nth_step(0).build.getWorkerCommandVersion = lambda cmd, oldversion: "2.15"  # type: ignore[method-assign, misc, union-attr]
        self.expect_commands(
            ExpectShell(workdir='wkdir', interrupt_signal='TERM', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectStat(file='wkdir/.git', log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                interrupt_signal='TERM',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                interrupt_signal='TERM',
                command=['git', 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir', interrupt_signal='TERM', command=['git', 'rev-parse', 'HEAD']
            )
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='incremental', progress=True
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_version_format(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='incremental')
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5.1')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_retry(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='incremental', retry=(0, 1)
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                branch='test-branch',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-B', 'test-branch']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_branch_ssh_key_2_10(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                branch='test-branch',
                sshPrivateKey='ssh-key',
                progress=True,
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_command_config = f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'checkout', '-B', 'test-branch'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_no_existing_repo_shallow_submodules(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                shallow=True,
                submodules=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--depth',
                    '1',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'update', '--init', '--recursive', '--depth', '1'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='fresh'
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_clean_fails(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='fresh'
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(
                1
            ),  # clean fails -> clobber
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_given_revision(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='incremental'),
            {"revision": 'abcdef01'},
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'cat-file', '-e', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_given_revision_not_exists(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='incremental'),
            {"revision": 'abcdef01'},
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'cat-file', '-e', 'abcdef01']).exit(1),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_submodule(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                submodules=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'foreach', '--recursive', 'git clean -f -f -d -x'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS, state_string="update")
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_submodule_git_newer_1_7_6(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                submodules=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.6')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'update', '--init', '--recursive', '--force'],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'foreach', '--recursive', 'git clean -f -f -d -x'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_submodule_v1_7_8(self) -> defer.Deferred[None]:
        """This tests the same as test_mode_full_fresh_submodule, but the
        "submodule update" command should be different for Git v1.7.8+."""
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                submodules=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.8')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'submodule',
                    'update',
                    '--init',
                    '--recursive',
                    '--force',
                    '--checkout',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'foreach', '--recursive', 'git clean -f -f -d -x'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_shallow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                shallow=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--depth',
                    '1',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_shallow_depth(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                shallow="100",  # type: ignore[arg-type]
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--depth',
                    '100',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_no_shallow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clobber'
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_retryFetch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                retryFetch=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(1),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_retryFetch_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                retryFetch=True,
                branch='test-branch',
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(1),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-B', 'test-branch']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    @defer.inlineCallbacks
    def test_fetch_or_fallback_clobbers_after_retry_failure(
        self,
    ) -> InlineCallbacksType[None]:
        step = self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                retryFetch=True,
                clobberOnFailure=True,
            )
        )
        fetch_calls: list[bool] = []
        clobber_calls = 0

        def fetch(
            _: Any,
            shallowClone: bool | int,
            abandonOnFailure: bool = True,
        ) -> defer.Deferred[int]:
            fetch_calls.append(abandonOnFailure)
            return defer.succeed(FAILURE)

        def clobber() -> defer.Deferred[None]:
            nonlocal clobber_calls
            clobber_calls += 1
            return defer.succeed(None)

        self.patch(step, '_fetch', fetch)
        self.patch(step, 'clobber', clobber)

        result = yield step._fetchOrFallback()

        self.assertEqual(fetch_calls, [False, False])
        self.assertEqual(clobber_calls, 1)
        self.assertEqual(result, SUCCESS)

    def test_mode_incremental_clobberOnFailure(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                clobberOnFailure=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_clobberOnFailure_branch(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                clobberOnFailure=True,
                branch='test-branch',
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'test-branch',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--branch',
                    'test-branch',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_copy(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='copy'
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='source', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectCpdir(fromdir='source', todir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_copy_ssh_key_2_10(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                sshPrivateKey='sshkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.source.buildbot'
        ssh_key_path = '/wrk/.bldr.source.buildbot/ssh-key'
        ssh_command_config = f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    '-c',
                    ssh_command_config,
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='source',
                command=['git', '-c', ssh_command_config, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectCpdir(fromdir='source', todir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_copy_shallow(self) -> None:
        with self.assertRaisesConfigError(
            "in mode 'full' shallow only possible with method 'clobber'"
        ):
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                shallow=True,
            )

    def test_mode_incremental_no_existing_repo(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='incremental')
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_incremental_no_existing_repo_oldworker(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='incremental')
        )
        self.get_nth_step(0).build.getWorkerCommandVersion = lambda cmd, oldversion: "2.15"  # type: ignore[method-assign, misc, union-attr]
        self.expect_commands(
            ExpectShell(workdir='wkdir', interrupt_signal='TERM', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectStat(file='wkdir/.git', log_environ=True).exit(1),
            ExpectShell(
                workdir='wkdir',
                interrupt_signal='TERM',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir', interrupt_signal='TERM', command=['git', 'rev-parse', 'HEAD']
            )
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_given_revision(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
            ),
            {"revision": 'abcdef01'},
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_revparse_failure(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
            ),
            {"revision": 'abcdef01'},
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ada95a1d')  # too short
            .exit(0),
        )
        self.expect_outcome(result=FAILURE)
        self.expect_no_property('got_revision')
        return self.run_step()

    def test_mode_full_clobber_submodule(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                submodules=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clobber_submodule_shallow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                submodules=True,
                shallow='1',  # type: ignore[arg-type]
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    '--depth',
                    '1',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'submodule', 'update', '--init', '--recursive', '--depth', '1'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_repourl(self) -> None:
        with self.assertRaisesConfigError("must provide repourl"):
            self.stepClass(mode="full")

    def test_mode_full_fresh_revision(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                progress=True,
            ),
            {"revision": 'abcdef01'},
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'abcdef01']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_retry(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                retry=(0, 2),
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_fresh_clobberOnFailure(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='fresh',
                clobberOnFailure=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files().exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_no_method(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='full')
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_with_env(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', env={'abc': '123'}
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'], env={'abc': '123'})
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'clean', '-f', '-f', '-d', '-x'],
                env={'abc': '123'},
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                env={'abc': '123'},
            ).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD'], env={'abc': '123'}
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'], env={'abc': '123'})
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_log_environ(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', logEnviron=False
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'], log_environ=False)
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=False).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d', '-x'], log_environ=False
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
                log_environ=False,
            ).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD'], log_environ=False
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'], log_environ=False)
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_wkdir_doesnt_exist(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(repourl='http://github.com/buildbot/buildbot.git', mode='full')
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').exit(1),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_getDescription(self) -> defer.Deferred[None]:
        # clone of: test_mode_incremental
        # only difference is to set the getDescription property

        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                getDescription=True,
            )
        )
        self.expect_commands(
            # copied from test_mode_incremental:
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            # plus this to test describe:
            ExpectShell(workdir='wkdir', command=['git', 'describe', 'HEAD'])
            .stdout('Tag-1234')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        self.expect_property('commit-description', 'Tag-1234', self.sourceName)
        return self.run_step()

    def test_getDescription_failed(self) -> defer.Deferred[None]:
        # clone of: test_mode_incremental
        # only difference is to set the getDescription property

        # this tests when 'git describe' fails; for example, there are no
        # tags in the repository

        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='incremental',
                getDescription=True,
            )
        )
        self.expect_commands(
            # copied from test_mode_incremental:
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            # plus this to test describe:
            ExpectShell(workdir='wkdir', command=['git', 'describe', 'HEAD'])
            .stdout('')
            .exit(128),  # error, but it's suppressed
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        self.expect_no_property('commit-description')
        return self.run_step()

    def setup_getDescription_test(
        self,
        setup_args: dict[str, Any],
        output_args: list[str],
        expect_head: bool = True,
        codebase: str | None = None,
    ) -> None:
        # clone of: test_mode_full_clobber
        # only difference is to set the getDescription property

        kwargs = {}  # type: ignore[var-annotated]
        if codebase is not None:
            kwargs.update(codebase=codebase)

        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                progress=True,
                getDescription=setup_args,
                **kwargs,
            )
        )

        self.expect_commands(
            # copied from test_mode_full_clobber:
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            # plus this to test describe:
            ExpectShell(
                workdir='wkdir',
                command=['git', 'describe'] + output_args + (['HEAD'] if expect_head else []),
            )
            .stdout('Tag-1234')
            .exit(0),
        )

        if codebase:
            self.expect_outcome(result=SUCCESS, state_string="update " + codebase)
            self.expect_property(
                'got_revision',
                {codebase: 'f6ad368298bd941e934a41f3babc827b2aa95a1d'},
                self.sourceName,
            )
            self.expect_property('commit-description', {codebase: 'Tag-1234'}, self.sourceName)
        else:
            self.expect_outcome(result=SUCCESS, state_string="update")
            self.expect_property(
                'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
            )
            self.expect_property('commit-description', 'Tag-1234', self.sourceName)

    def test_getDescription_empty_dict(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={}, output_args=[])
        return self.run_step()

    def test_getDescription_empty_dict_with_codebase(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={}, output_args=[], codebase='baz')
        return self.run_step()

    def test_getDescription_match(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'match': 'stuff-*'}, output_args=['--match', 'stuff-*']
        )
        return self.run_step()

    def test_getDescription_match_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'match': None}, output_args=[])
        return self.run_step()

    def test_getDescription_exclude(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'exclude': 'stuff-*'}, output_args=['--exclude', 'stuff-*']
        )
        return self.run_step()

    def test_getDescription_exclude_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'exclude': None}, output_args=[])
        return self.run_step()

    def test_getDescription_tags(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'tags': True}, output_args=['--tags'])
        return self.run_step()

    def test_getDescription_tags_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'tags': False}, output_args=[])
        return self.run_step()

    def test_getDescription_all(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'all': True}, output_args=['--all'])
        return self.run_step()

    def test_getDescription_all_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'all': False}, output_args=[])
        return self.run_step()

    def test_getDescription_abbrev(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'abbrev': 7}, output_args=['--abbrev=7'])
        return self.run_step()

    def test_getDescription_abbrev_zero(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'abbrev': 0}, output_args=['--abbrev=0'])
        return self.run_step()

    def test_getDescription_abbrev_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'abbrev': False}, output_args=[])
        return self.run_step()

    def test_getDescription_dirty(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'dirty': True}, output_args=['--dirty'], expect_head=False
        )
        return self.run_step()

    def test_getDescription_dirty_empty_str(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'dirty': ''}, output_args=['--dirty'], expect_head=False
        )
        return self.run_step()

    def test_getDescription_dirty_str(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'dirty': 'foo'}, output_args=['--dirty=foo'], expect_head=False
        )
        return self.run_step()

    def test_getDescription_dirty_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'dirty': False}, output_args=[], expect_head=True
        )
        return self.run_step()

    def test_getDescription_dirty_none(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'dirty': None}, output_args=[], expect_head=True)
        return self.run_step()

    def test_getDescription_contains(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'contains': True}, output_args=['--contains'])
        return self.run_step()

    def test_getDescription_contains_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'contains': False}, output_args=[])
        return self.run_step()

    def test_getDescription_candidates(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'candidates': 7}, output_args=['--candidates=7'])
        return self.run_step()

    def test_getDescription_candidates_zero(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'candidates': 0}, output_args=['--candidates=0'])
        return self.run_step()

    def test_getDescription_candidates_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'candidates': False}, output_args=[])
        return self.run_step()

    def test_getDescription_exact_match(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'exact-match': True}, output_args=['--exact-match']
        )
        return self.run_step()

    def test_getDescription_exact_match_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'exact-match': False}, output_args=[])
        return self.run_step()

    def test_getDescription_first_parent(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'first-parent': True}, output_args=['--first-parent']
        )
        return self.run_step()

    def test_getDescription_first_parent_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'first-parent': False}, output_args=[])
        return self.run_step()

    def test_getDescription_debug(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'debug': True}, output_args=['--debug'])
        return self.run_step()

    def test_getDescription_debug_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'debug': False}, output_args=[])
        return self.run_step()

    def test_getDescription_long(self) -> None:
        self.setup_getDescription_test(setup_args={'long': True}, output_args=['--long'])

    def test_getDescription_long_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'long': False}, output_args=[])
        return self.run_step()

    def test_getDescription_always(self) -> None:
        self.setup_getDescription_test(setup_args={'always': True}, output_args=['--always'])

    def test_getDescription_always_false(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(setup_args={'always': False}, output_args=[])
        return self.run_step()

    def test_getDescription_lotsa_stuff(self) -> defer.Deferred[None]:
        self.setup_getDescription_test(
            setup_args={'match': 'stuff-*', 'abbrev': 6, 'exact-match': True},
            output_args=['--exact-match', '--match', 'stuff-*', '--abbrev=6'],
            codebase='baz',
        )
        return self.run_step()

    def test_config_option(self) -> defer.Deferred[None]:
        name = 'url.http://github.com.insteadOf'
        value = 'blahblah'
        self.setup_step(
            self.stepClass(
                repourl=f'{value}/buildbot/buildbot.git',
                mode='full',
                method='clean',
                config={name: value},
            )
        )
        prefix = ['git', '-c', f'{name}={value}']
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=[*prefix, '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=[*prefix, 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    *prefix,
                    'fetch',
                    '-f',
                    '--progress',
                    f'{value}/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=[*prefix, 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='wkdir', command=[*prefix, 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_worker_connection_lost(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .error(error.ConnectionLost())
        )
        self.expect_outcome(result=RETRY, state_string="update (retry)")
        return self.run_step()

    @defer.inlineCallbacks
    def _test_WorkerSetupError(
        self, _dovccmd: Any, step: Any, msg: Any
    ) -> InlineCallbacksType[None]:
        self.patch(self.stepClass, "_dovccmd", _dovccmd)
        gitStep = self.setup_step(step)

        with self.assertRaisesRegex(WorkerSetupError, msg):
            yield gitStep.run_vc("branch", "revision", "patch")

    def test_noGitCommandInstalled(self) -> defer.Deferred[None]:
        @defer.inlineCallbacks
        def _dovccmd(
            command: list[str],
            abandonOnFailure: bool = True,
            collectStdout: bool = False,
            initialStdin: str | None = None,
        ) -> InlineCallbacksType[str]:
            """
            Simulate the case where there is no git command.
            """
            yield  # type: ignore[misc]
            return "command not found:"

        step = self.stepClass(
            repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
        )
        msg = 'git is not installed on worker'
        return self._test_WorkerSetupError(_dovccmd, step, msg)

    def test_gitCommandOutputShowsNoVersion(self) -> defer.Deferred[None]:
        @defer.inlineCallbacks
        def _dovccmd(
            command: list[str],
            abandonOnFailure: bool = True,
            collectStdout: bool = False,
            initialStdin: str | None = None,
        ) -> InlineCallbacksType[str]:
            """
            Instead of outputting something like "git version 2.11",
            simulate truncated output which has no version string,
            to exercise error handling.
            """
            yield  # type: ignore[misc]
            return "git "

        step = self.stepClass(
            repourl='http://github.com/buildbot/buildbot.git', mode='full', method='clean'
        )
        msg = 'git is not installed on worker'
        return self._test_WorkerSetupError(_dovccmd, step, msg)

    def test_config_get_description_not_dict_or_boolean(self) -> None:
        with self.assertRaisesConfigError("Git: getDescription must be a boolean or a dict."):
            self.stepClass(
                repourl="http://github.com/buildbot/buildbot.git",
                getDescription=["list"],  # type: ignore[arg-type]
            )

    def test_config_invalid_method_with_full(self) -> None:
        with self.assertRaisesConfigError("Git: invalid method for mode 'full'."):
            self.stepClass(
                repourl="http://github.com/buildbot/buildbot.git", mode='full', method='unknown'
            )

    def test_mode_full_copy_recursive(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                submodules='True',  # type: ignore[arg-type]
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(workdir='source', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='source', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='source', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectCpdir(fromdir='source', todir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_copy_recursive_fetch_fail(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                submodules='True',  # type: ignore[arg-type]
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_mode_full_copy_recursive_fetch_fail_retry_fail(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                submodules='True',  # type: ignore[arg-type]
                retryFetch=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(1),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_mode_full_copy_recursive_fetch_fail_retry_succeed(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                submodules='True',  # type: ignore[arg-type]
                retryFetch=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(1),
            # retry Fetch
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(0),
            # continue as normal
            ExpectShell(workdir='source', command=['git', 'checkout', '-f', 'FETCH_HEAD']).exit(0),
            ExpectShell(workdir='source', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='source', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectCpdir(fromdir='source', todir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_mode_full_copy_recursive_fetch_fail_clobberOnFailure(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='copy',
                submodules='True',  # type: ignore[arg-type]
                clobberOnFailure=True,
            )
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200),
            ExpectListdir(dir='source').files(['.git']).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'fetch',
                    '-f',
                    '--progress',
                    'http://github.com/buildbot/buildbot.git',
                    'HEAD',
                ],
            ).exit(1),
            # clobber and re-clone the source dir here
            ExpectRmdir(dir='source', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='source',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(
                workdir='source', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectShell(workdir='source', command=['git', 'submodule', 'sync']).exit(0),
            ExpectShell(
                workdir='source', command=['git', 'submodule', 'update', '--init', '--recursive']
            ).exit(0),
            ExpectCpdir(fromdir='source', todir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    @parameterized.expand([
        ('', None),
        ('use_http_path', True),
        ('dont_use_http_path', False),
    ])
    def test_mode_full_clean_auth_credential(
        self, name: str, use_http_path: bool | None
    ) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='https://example.com/test/test.git',
                mode='full',
                method='clean',
                auth_credentials=('username', 'token'),
                git_credentials=GitCredentialOptions(
                    credentials=[],
                    use_http_path=use_http_path,
                ),
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        git_credential_path = '/wrk/.bldr.wkdir.buildbot/.git-credentials'

        use_http_path_arg = [
            '-c',
            'credential.helper=',
            '-c',
            f'credential.helper=store "--file={git_credential_path}"',
        ]
        if use_http_path is not None:
            use_http_path_arg.append('-c')
            if use_http_path:
                use_http_path_arg.append('credential.useHttpPath=true')
            else:
                use_http_path_arg.append('credential.useHttpPath=false')

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *use_http_path_arg,
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/test.git\nusername=username\npassword=token\n"
                ),
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *use_http_path_arg,
                    'fetch',
                    '-f',
                    '--progress',
                    'https://example.com/test/test.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', *use_http_path_arg, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_git_credential(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='https://example.com/test/test.git',
                mode='full',
                method='clean',
                git_credentials=GitCredentialOptions(
                    credentials=[
                        (
                            "url=https://example.com/test/test.git\n"
                            "username=username\n"
                            "password=token\n"
                        ),
                    ],
                ),
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        git_credential_path = '/wrk/.bldr.wkdir.buildbot/.git-credentials'
        git_credentials_config_args = [
            '-c',
            'credential.helper=',
            '-c',
            f'credential.helper=store "--file={git_credential_path}"',
        ]

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *git_credentials_config_args,
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/test.git\nusername=username\npassword=token\n"
                ),
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *git_credentials_config_args,
                    'fetch',
                    '-f',
                    '--progress',
                    'https://example.com/test/test.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', *git_credentials_config_args, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()

    def test_mode_full_clean_auth_and_git_credential(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='https://example.com/test/test.git',
                mode='full',
                method='clean',
                auth_credentials=('auth_username', 'auth_token'),
                git_credentials=GitCredentialOptions(
                    credentials=[
                        (
                            "url=https://example.com/test/submodule_test.git\n"
                            "username=username\n"
                            "password=token\n"
                        ),
                    ],
                    use_http_path=True,
                ),
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        git_credential_path = '/wrk/.bldr.wkdir.buildbot/.git-credentials'
        git_credentials_config_args = [
            '-c',
            'credential.helper=',
            '-c',
            f'credential.helper=store "--file={git_credential_path}"',
            '-c',
            'credential.useHttpPath=true',
        ]

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *git_credentials_config_args,
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/test.git\n"
                    "username=auth_username\n"
                    "password=auth_token\n"
                ),
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *git_credentials_config_args,
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/submodule_test.git\n"
                    "username=username\n"
                    "password=token\n"
                ),
            ).exit(0),
            ExpectListdir(dir='wkdir').files(['.git']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'clean', '-f', '-f', '-d']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    *git_credentials_config_args,
                    'fetch',
                    '-f',
                    '--progress',
                    'https://example.com/test/test.git',
                    'HEAD',
                ],
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', *git_credentials_config_args, 'checkout', '-f', 'FETCH_HEAD'],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        self.expect_property(
            'got_revision', 'f6ad368298bd941e934a41f3babc827b2aa95a1d', self.sourceName
        )
        return self.run_step()


class TestGitPush(
    TestBuildStepMixin, config.ConfigErrorsMixin, TestReactorMixin, unittest.TestCase
):
    stepClass = git.GitPush

    def setUp(self) -> defer.Deferred[None]:  # type: ignore[override]
        self.setup_test_reactor()
        return self.setup_test_build_step()

    @parameterized.expand([
        ('url', 'ssh://github.com/test/test.git', 'ssh://github.com/test/test.git'),
        (
            'url_renderable',
            Interpolate('ssh://github.com/test/test.git'),
            'ssh://github.com/test/test.git',
        ),
        ('host_path', 'host:path/to/git', 'ssh://host:22/path/to/git'),
        ('host_path_renderable', Interpolate('host:path/to/git'), 'ssh://host:22/path/to/git'),
    ])
    def test_push_simple(
        self, name: str, url: str | Interpolate, push_url: str
    ) -> defer.Deferred[None]:
        self.setup_step(self.stepClass(workdir='wkdir', repourl=url, branch='testbranch'))
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'push', push_url, 'testbranch']).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_force(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'

        self.setup_step(
            self.stepClass(workdir='wkdir', repourl=url, branch='testbranch', force=True)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'push', url, 'testbranch', '--force']
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_fail(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'

        self.setup_step(
            self.stepClass(workdir='wkdir', repourl=url, branch='testbranch', force=True)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'push', url, 'testbranch', '--force'])
            .stderr("error: failed to push some refs to <url>\n")
            .exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_push_ssh_key_2_10(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'

        self.setup_step(
            self.stepClass(
                workdir='wkdir', repourl=url, branch='testbranch', sshPrivateKey='sshKey'
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_command_config = f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'push', url, 'testbranch'],
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_ssh_key_2_3(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'

        self.setup_step(
            self.stepClass(
                workdir='wkdir', repourl=url, branch='testbranch', sshPrivateKey='sshKey'
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_command = f'ssh -o "BatchMode=yes" -i "{ssh_key_path}"'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.3.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'push', url, 'testbranch'],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_ssh_key_1_7(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'

        self.setup_step(
            self.stepClass(
                workdir='wkdir', repourl=url, branch='testbranch', sshPrivateKey='sshKey'
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_wrapper_path = '/wrk/.bldr.wkdir.buildbot/ssh-wrapper.sh'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'push', url, 'testbranch'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_ssh_host_key_2_10(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                repourl=url,
                branch='testbranch',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'
        ssh_command_config = (
            f'core.sshCommand=ssh -o "BatchMode=yes" -i "{ssh_key_path}" '
            f'-o "UserKnownHostsFile={ssh_known_hosts_path}"'
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.10.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', '-c', ssh_command_config, 'push', url, 'testbranch'],
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_ssh_host_key_2_3(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                repourl=url,
                branch='testbranch',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'
        ssh_command = (
            f'ssh -o "BatchMode=yes" -i "{ssh_key_path}" '
            f'-o "UserKnownHostsFile={ssh_known_hosts_path}"'
        )

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.3.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'push', url, 'testbranch'],
                env={'GIT_SSH_COMMAND': ssh_command},
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_ssh_host_key_1_7(self) -> defer.Deferred[None]:
        url = 'ssh://github.com/test/test.git'
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                repourl=url,
                branch='testbranch',
                sshPrivateKey='sshkey',
                sshHostKey='sshhostkey',
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        ssh_key_path = '/wrk/.bldr.wkdir.buildbot/ssh-key'
        ssh_wrapper_path = '/wrk/.bldr.wkdir.buildbot/ssh-wrapper.sh'
        ssh_known_hosts_path = '/wrk/.bldr.wkdir.buildbot/ssh-known-hosts'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.0')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_key_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_known_hosts_path,
                workdir=ssh_workdir,
                mode=0o400,
            ).exit(0),
            ExpectDownloadFile(
                blocksize=32768,
                maxsize=None,
                reader=ExpectRemoteRef(remotetransfer.StringFileReader),
                workerdest=ssh_wrapper_path,
                workdir=ssh_workdir,
                mode=0o700,
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'push', url, 'testbranch'],
                env={'GIT_SSH': ssh_wrapper_path},
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_raise_no_git(self) -> None:
        @defer.inlineCallbacks
        def _checkFeatureSupport(self: Any) -> InlineCallbacksType[bool]:
            yield  # type: ignore[misc]
            return False

        url = 'ssh://github.com/test/test.git'
        step = self.stepClass(workdir='wkdir', repourl=url, branch='testbranch')
        self.patch(self.stepClass, "checkFeatureSupport", _checkFeatureSupport)
        self.setup_step(step)
        self.expect_outcome(result=EXCEPTION)
        self.run_step()
        self.flushLoggedErrors(WorkerSetupError)

    def test_config_fail_no_branch(self) -> None:
        with self.assertRaisesConfigError("GitPush: must provide branch"):
            self.stepClass(workdir='wkdir', repourl="url")

    @parameterized.expand([
        ('', None),
        ('use_http_path', True),
        ('dont_use_http_path', False),
    ])
    def test_push_auth_credential(
        self, name: str, use_http_path: bool | None
    ) -> defer.Deferred[None]:
        url = 'https://example.com/test/test.git'
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                repourl=url,
                branch='testbranch',
                auth_credentials=('username', 'token'),
                git_credentials=GitCredentialOptions(
                    credentials=[],
                    use_http_path=use_http_path,
                ),
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        git_credential_path = '/wrk/.bldr.wkdir.buildbot/.git-credentials'

        use_http_path_arg = []
        if use_http_path is not None:
            use_http_path_arg.append('-c')
            if use_http_path:
                use_http_path_arg.append('credential.useHttpPath=true')
            else:
                use_http_path_arg.append('credential.useHttpPath=false')

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.9')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    'credential.helper=',
                    '-c',
                    f'credential.helper=store "--file={git_credential_path}"',
                    *use_http_path_arg,
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/test.git\nusername=username\npassword=token\n"
                ),
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    'credential.helper=',
                    '-c',
                    f'credential.helper=store "--file={git_credential_path}"',
                    *use_http_path_arg,
                    'push',
                    url,
                    'testbranch',
                ],
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_push_git_credential(self) -> defer.Deferred[None]:
        url = 'https://example.com/test/test.git'
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                repourl=url,
                branch='testbranch',
                git_credentials=GitCredentialOptions(
                    credentials=[
                        (
                            "url=https://example.com/test/test.git\n"
                            "username=username\n"
                            "password=token\n"
                        ),
                    ]
                ),
            )
        )

        ssh_workdir = '/wrk/.bldr.wkdir.buildbot'
        git_credential_path = '/wrk/.bldr.wkdir.buildbot/.git-credentials'

        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.9')
            .exit(0),
            ExpectMkdir(dir=ssh_workdir, log_environ=True).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    'credential.helper=',
                    '-c',
                    f'credential.helper=store "--file={git_credential_path}"',
                    'credential',
                    'approve',
                ],
                initial_stdin=(
                    "url=https://example.com/test/test.git\nusername=username\npassword=token\n"
                ),
            ).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    '-c',
                    'credential.helper=',
                    '-c',
                    f'credential.helper=store "--file={git_credential_path}"',
                    'push',
                    url,
                    'testbranch',
                ],
            ).exit(0),
            ExpectRmdir(dir=ssh_workdir, log_environ=True).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()


class TestGitTag(TestBuildStepMixin, config.ConfigErrorsMixin, TestReactorMixin, unittest.TestCase):
    stepClass = git.GitTag

    def setUp(self) -> defer.Deferred[None]:  # type: ignore[override]
        self.setup_test_reactor()
        return self.setup_test_build_step()

    def test_tag_annotated(self) -> defer.Deferred[None]:
        messages = ['msg1', 'msg2']

        self.setup_step(
            self.stepClass(workdir='wkdir', tagName='myTag', annotated=True, messages=messages)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'tag', '-a', 'myTag', '-m', 'msg1', '-m', 'msg2']
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_tag_simple(self) -> defer.Deferred[None]:
        self.setup_step(self.stepClass(workdir='wkdir', tagName='myTag'))
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'tag', 'myTag']).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_tag_force(self) -> defer.Deferred[None]:
        self.setup_step(self.stepClass(workdir='wkdir', tagName='myTag', force=True))
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'tag', 'myTag', '--force']).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_tag_fail_already_exist(self) -> defer.Deferred[None]:
        self.setup_step(self.stepClass(workdir='wkdir', tagName='myTag'))
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'tag', 'myTag'])
            .stderr("fatal: tag '%s' already exist\n")
            .exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_config_annotated_no_messages(self) -> None:
        with self.assertRaises(bbconfig.ConfigErrors):
            self.setup_step(self.stepClass(workdir='wkdir', tagName='myTag', annotated=True))

    def test_config_no_tag_name(self) -> None:
        with self.assertRaises(bbconfig.ConfigErrors):
            self.setup_step(self.stepClass(workdir='wkdir'))

    def test_config_not_annotated_but_meessages(self) -> None:
        with self.assertRaises(bbconfig.ConfigErrors):
            self.setup_step(self.stepClass(workdir='wkdir', tagName='myTag', messages=['msg']))

    def test_config_annotated_message_not_list(self) -> None:
        with self.assertRaises(bbconfig.ConfigErrors):
            self.setup_step(
                self.stepClass(workdir='wkdir', tagName='myTag', annotated=True, messages="msg")  # type: ignore[arg-type]
            )

    def test_raise_no_git(self) -> None:
        @defer.inlineCallbacks
        def _checkFeatureSupport(self: Any) -> InlineCallbacksType[bool]:
            yield  # type: ignore[misc]
            return False

        step = self.stepClass(workdir='wdir', tagName='myTag')
        self.patch(self.stepClass, "checkFeatureSupport", _checkFeatureSupport)
        self.setup_step(step)
        self.expect_outcome(result=EXCEPTION)
        self.run_step()
        self.flushLoggedErrors(WorkerSetupError)


class TestGitCommit(
    TestBuildStepMixin, config.ConfigErrorsMixin, TestReactorMixin, unittest.TestCase
):
    stepClass = git.GitCommit

    def setUp(self) -> defer.Deferred[None]:  # type: ignore[override]
        self.setup_test_reactor()
        self.message_list = ['my commit', '42']
        self.path_list = ['file1.txt', 'file2.txt']

        return self.setup_test_build_step()

    def test_add_fail(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(workdir='wkdir', paths=self.path_list, messages=self.message_list)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_commit(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(workdir='wkdir', paths=self.path_list, messages=self.message_list)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'commit', '-m', 'my commit', '-m', '42']
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_commit_noverify(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir', paths=self.path_list, messages=self.message_list, no_verify=True
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'commit', '-m', 'my commit', '-m', '42', '--no-verify'],
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_commit_empty_disallow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                paths=self.path_list,
                messages=self.message_list,
                emptyCommits='disallow',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'commit', '-m', 'my commit', '-m', '42']
            ).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_commit_empty_allow(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                paths=self.path_list,
                messages=self.message_list,
                emptyCommits='create-empty-commit',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=['git', 'commit', '-m', 'my commit', '-m', '42', '--allow-empty'],
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_commit_empty_ignore_withcommit(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                paths=self.path_list,
                messages=self.message_list,
                emptyCommits='ignore',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'status', '--porcelain=v1'])
            .stdout('MM file2.txt\n?? file3.txt')
            .exit(0),
            ExpectShell(
                workdir='wkdir', command=['git', 'commit', '-m', 'my commit', '-m', '42']
            ).exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_commit_empty_ignore_withoutcommit(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                paths=self.path_list,
                messages=self.message_list,
                emptyCommits='ignore',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'status', '--porcelain=v1'])
            .stdout('?? file3.txt')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_commit_empty_ignore_witherror(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                workdir='wkdir',
                paths=self.path_list,
                messages=self.message_list,
                emptyCommits='ignore',
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('refs/head/myBranch')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'add', 'file1.txt', 'file2.txt']).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'status', '--porcelain=v1']).exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_detached_head(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(workdir='wkdir', paths=self.path_list, messages=self.message_list)
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 1.7.5')
            .exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'symbolic-ref', 'HEAD'])
            .stdout('')
            .exit(1),
        )
        self.expect_outcome(result=FAILURE)
        return self.run_step()

    def test_config_no_files_arg(self) -> None:
        with self.assertRaisesConfigError("GitCommit: must provide paths"):
            self.stepClass(workdir='wkdir', messages=self.message_list)

    def test_config_files_not_a_list(self) -> None:
        with self.assertRaisesConfigError("GitCommit: paths must be a list"):
            self.stepClass(workdir='wkdir', paths="test.txt", messages=self.message_list)  # type: ignore[arg-type]

    def test_config_no_messages_arg(self) -> None:
        with self.assertRaisesConfigError("GitCommit: must provide messages"):
            self.stepClass(workdir='wkdir', paths=self.path_list)

    def test_config_messages_not_a_list(self) -> None:
        with self.assertRaisesConfigError("GitCommit: messages must be a list"):
            self.stepClass(workdir='wkdir', paths=self.path_list, messages="my message")  # type: ignore[arg-type]

    def test_raise_no_git(self) -> None:
        @defer.inlineCallbacks
        def _checkFeatureSupport(self: Any) -> InlineCallbacksType[bool]:
            yield  # type: ignore[misc]
            return False

        step = self.stepClass(workdir='wkdir', paths=self.path_list, messages=self.message_list)
        self.patch(self.stepClass, "checkFeatureSupport", _checkFeatureSupport)
        self.setup_step(step)
        self.expect_outcome(result=EXCEPTION)
        self.run_step()
        self.flushLoggedErrors(WorkerSetupError)


class TestGitSharedCache(
    sourcesteps.SourceStepMixin, config.ConfigErrorsMixin, TestReactorMixin, unittest.TestCase
):
    stepClass = git.Git

    def setUp(self) -> defer.Deferred[None]:  # type: ignore[override]
        self.setup_test_reactor()
        self.sourceName = self.stepClass.__name__
        return self.setup_test_build_step()

    def test_old_git_ignores_shared_cache_end_to_end(self) -> defer.Deferred[None]:
        self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                mode='full',
                method='clobber',
                shared_cache=True,
            )
        )
        self.expect_commands(
            ExpectShell(workdir='wkdir', command=['git', '--version'])
            .stdout('git version 2.11.0')
            .exit(0),
            ExpectStat(file='wkdir/.buildbot-patched', log_environ=True).exit(1),
            ExpectRmdir(dir='wkdir', log_environ=True, timeout=1200).exit(0),
            ExpectShell(
                workdir='wkdir',
                command=[
                    'git',
                    'clone',
                    'http://github.com/buildbot/buildbot.git',
                    '.',
                    '--progress',
                ],
            ).exit(0),
            ExpectShell(workdir='wkdir', command=['git', 'rev-parse', 'HEAD'])
            .stdout('f6ad368298bd941e934a41f3babc827b2aa95a1d')
            .exit(0),
        )
        self.expect_outcome(result=SUCCESS)
        return self.run_step()

    def test_shared_cache_preserves_positional_submodules_argument(self) -> None:
        step = self.stepClass(
            'http://github.com/buildbot/buildbot.git',
            22,
            'HEAD',
            'incremental',
            None,
            None,
            True,
        )

        self.assertTrue(step.submodules)
        self.assertFalse(step.shared_cache)

    @parameterized.expand([
        (
            'default',
            True,
            '/wrk/.git-cache/51509057e6aa2288.git',
        ),
        ('relative_custom', 'shared/repo.git', '/wrk/shared/repo.git'),
        ('absolute_custom', '/srv/git/repo.git', '/srv/git/repo.git'),
    ])
    def test_shared_cache_path(
        self, name: str, shared_cache: bool | str, expected_path: str
    ) -> None:
        step = self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                shared_cache=shared_cache,
            )
        )

        self.assertEqual(step._computeCachePath(), expected_path)

    def test_shared_cache_path_uses_windows_worker_root(self) -> None:
        step = self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                shared_cache='shared/repo.git',
            )
        )
        self.change_worker_system('nt')
        self.worker.worker_basedir = r'C:\wrk'

        self.assertEqual(step._computeCachePath(), r'C:\wrk\shared\repo.git')

    def test_shared_cache_rejects_incomplete_windows_worker_root(self) -> None:
        step = self.setup_step(
            self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                shared_cache=True,
            )
        )
        self.change_worker_system('nt')
        self.worker.worker_basedir = r'\\server'

        with self.assertRaisesRegex(ValueError, 'requires an absolute worker basedir'):
            step._computeCachePath()

    @parameterized.expand([
        ('drive_relative', r'C:cache'),
        ('root_relative_backslash', r'\cache'),
        ('root_relative_slash', '/cache'),
        ('incomplete_unc', r'\\server'),
    ])
    def test_windows_shared_cache_path_rejects_partially_qualified_path(
        self, name: str, cache_path: str
    ) -> None:
        step = self.setup_step(
            self.stepClass(
                repourl='https://github.com/buildbot/buildbot.git',
                shared_cache=cache_path,
            )
        )
        self.change_worker_system('nt')
        self.worker.worker_basedir = r'C:\wrk'

        with self.assertRaisesRegex(
            buildstep.BuildStepFailed,
            'Windows shared_cache paths must be fully qualified or relative',
        ):
            step._validateRenderedSharedCache()

        with self.assertRaisesRegex(
            ValueError,
            'Windows shared_cache paths must be fully qualified or relative',
        ):
            step._computeCachePath()

    @parameterized.expand([
        (
            'http_ipv6_with_port',
            'https://user:secret@[2001:db8::1]:8443/repo.git',
            'https://[2001:db8::1]:8443/repo.git',
        ),
        (
            'ssh_username_preserved',
            'ssh://git@example.com:2222/buildbot/buildbot.git',
            'ssh://git@example.com:2222/buildbot/buildbot.git',
        ),
        (
            'scheme_normalized',
            'HTTPS://Example.COM/repo.git',
            'https://example.com/repo.git',
        ),
        (
            'scp_style_without_scheme',
            'git@example.com:buildbot/buildbot.git',
            'git@example.com:buildbot/buildbot.git',
        ),
        (
            'malformed_port_keeps_host_text',
            'ssh://git@host:notaport/repo.git',
            'ssh://git@host:notaport/repo.git',
        ),
        (
            'malformed_port_still_drops_userinfo',
            'https://user:secret@example.com:notaport/repo.git',
            'https://example.com:notaport/repo.git',
        ),
        (
            'default_ssh_port_dropped',
            'ssh://git@example.com:22/buildbot/buildbot.git',
            'ssh://git@example.com/buildbot/buildbot.git',
        ),
        (
            'default_https_port_dropped',
            'https://example.com:443/repo.git',
            'https://example.com/repo.git',
        ),
        (
            'non_default_port_kept',
            'https://example.com:8443/repo.git',
            'https://example.com:8443/repo.git',
        ),
        (
            'malformed_bracket_host',
            'https://[server]/repo.git',
            'https://[server]/repo.git',
        ),
        (
            'ipv6_literal_host',
            'https://[::1]:8443/repo.git',
            'https://[::1]:8443/repo.git',
        ),
    ])
    def test_shared_cache_identity_edge_cases(
        self, name: str, repourl: str, expected_identity: str
    ) -> None:
        step = self.stepClass(repourl=repourl, shared_cache=True)

        self.assertEqual(step._getSharedCacheIdentity(), expected_identity)

    def test_shared_cache_identity_ignores_http_credential_scope(self) -> None:
        identities = {
            self.stepClass(repourl=repourl, shared_cache=True)._getSharedCacheIdentity()
            for repourl in (
                'https://alice:secret-a@example.com/repo.git',
                'https://bob:secret-b@example.com/repo.git',
            )
        }

        self.assertEqual(identities, {'https://example.com/repo.git'})

    def test_shared_cache_requires_valid_type(self) -> None:
        self.assertRaisesConfigError(
            'Git: shared_cache must be a boolean, string, or renderable',
            lambda: self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                shared_cache=object(),  # type: ignore[arg-type]
            ),
        )

    @parameterized.expand([
        ('invalid_type', 1, None, 'rendered shared_cache must be a boolean or string'),
        (
            'invalid_path',
            'cache\npath',
            None,
            'rendered shared_cache path must not contain NUL or newline characters',
        ),
        ('reference_conflict', True, 'some/ref', 'shared_cache and reference cannot both be set'),
    ])
    def test_validate_rendered_shared_cache(
        self,
        name: str,
        shared_cache: Any,
        reference: str | None,
        expected_error: str,
    ) -> None:
        step = self.stepClass(
            repourl='https://github.com/buildbot/buildbot.git',
            shared_cache=True,
        )
        object.__setattr__(step, 'shared_cache', shared_cache)
        object.__setattr__(step, 'reference', reference)

        with self.assertRaisesRegex(buildstep.BuildStepFailed, expected_error):
            step._validateRenderedSharedCache()

    @parameterized.expand([
        ('query', 'https://example.com/repo.git?token=secret'),
        ('fragment', 'https://example.com/repo.git#credential'),
    ])
    def test_validate_shared_cache_rejects_http_url_suffix(self, name: str, repourl: str) -> None:
        step = self.setup_step(self.stepClass(repourl=repourl, shared_cache=True))

        with self.assertRaisesRegex(
            buildstep.BuildStepFailed,
            r'shared_cache does not support HTTP\(S\) repository URLs with a query or fragment',
        ):
            step._validateRenderedSharedCache()

    def test_validate_shared_cache_allows_malformed_bracket_repourl(self) -> None:
        step = self.setup_step(
            self.stepClass(repourl='https://[server]/repo.git', shared_cache=True)
        )

        step._validateRenderedSharedCache()

        self.assertEqual(step._getSharedCacheIdentity(), 'https://[server]/repo.git')

    def test_validate_http_url_suffix_without_shared_cache(self) -> None:
        step = self.setup_step(
            self.stepClass(
                repourl='https://example.com/repo.git?token=secret',
                shared_cache=False,
            )
        )

        step._validateRenderedSharedCache()

    @parameterized.expand([
        ('posix_relative', 'posix', '../repository.git', True),
        ('posix_relative_with_colon', 'posix', './repository:name.git', True),
        ('posix_absolute', 'posix', '/srv/git/repository.git', False),
        ('scp_remote', 'posix', 'git@example.com:repository.git', False),
        ('windows_relative', 'nt', r'..\repository.git', True),
        ('windows_drive_relative', 'nt', r'C:repository.git', True),
        ('windows_root_relative_backslash', 'nt', r'\repository.git', True),
        ('windows_root_relative_slash', 'nt', '/repository.git', True),
        ('windows_incomplete_unc', 'nt', r'\\server', True),
        ('windows_absolute', 'nt', r'C:\repository.git', False),
        ('windows_unc', 'nt', r'\\server\share\repository.git', False),
    ])
    def test_validate_shared_cache_repository_location(
        self,
        name: str,
        worker_system: str,
        repourl: str,
        invalid: bool,
    ) -> None:
        step = self.setup_step(self.stepClass(repourl=repourl, shared_cache=True))
        self.change_worker_system(worker_system)

        if invalid:
            with self.assertRaisesRegex(
                buildstep.BuildStepFailed,
                'shared_cache does not support relative local repository paths',
            ):
                step._validateRenderedSharedCache()
        else:
            step._validateRenderedSharedCache()

    @defer.inlineCallbacks
    def test_run_vc_rejects_relative_repository_before_scp_conversion(
        self,
    ) -> InlineCallbacksType[None]:
        step = self.setup_step(
            self.stepClass(
                repourl='./repository:name.git',
                shared_cache=True,
            )
        )
        setup_repourl_called = False

        def setup_repourl() -> None:
            nonlocal setup_repourl_called
            setup_repourl_called = True

        self.patch(step, 'setup_repourl', setup_repourl)

        headers: list[str] = []
        original_add_log = step.addLogForRemoteCommands

        @defer.inlineCallbacks
        def add_log(name: str) -> InlineCallbacksType[Any]:
            stdio_log = yield original_add_log(name)
            object.__setattr__(stdio_log, 'addHeader', headers.append)
            return stdio_log

        self.patch(step, 'addLogForRemoteCommands', add_log)

        failure = yield self.assertFailure(
            step.run_vc('main', None, None),
            buildstep.BuildStepFailed,
        )
        self.assertIn(
            'shared_cache does not support relative local repository paths',
            str(failure),
        )
        self.assertFalse(setup_repourl_called)
        self.assertTrue(
            any('relative local repository paths' in header for header in headers),
        )

    def test_shared_cache_with_reference_error(self) -> None:
        self.assertRaisesConfigError(
            'Git: shared_cache and reference cannot both be set',
            lambda: self.stepClass(
                repourl='http://github.com/buildbot/buildbot.git',
                shared_cache=True,
                reference='some/ref',
            ),
        )
