from emmett import Pipe, abort


class VPNAuthPipe(Pipe):
    def __init__(self, config, default):
        self.config = config
        self.default = default
        self.groups_match = {}
        for key, data in self.config.items():
            for group in data.get("groups", []):
                self.groups_match[group] = key

    def match_vpn_profile(self, groups):
        matches = []
        for group in groups:
            if group in self.groups_match:
                matches.append(self.groups_match[group])
        if not matches:
            return self.default
        return sorted([
            (key, self.config[key].get("priority", 100)) for key in matches
        ], key=lambda v: v[1])[0][0]

    async def pipe_request(self, next_pipe, email, groups, **kwargs):
        vpn_profile = self.match_vpn_profile(groups)
        if not vpn_profile:
            abort(401)
        return await next_pipe(vpn_profile=vpn_profile, vpn_cn=email, **kwargs)
