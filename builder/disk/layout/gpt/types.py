from uuid import UUID
from logging import getLogger
from builder.disk.layout.gpt.uefi import EfiGUID
from builder.disk.layout.types import DiskTypes
log = getLogger(__name__)


class DiskTypesGPT(DiskTypes):
	@staticmethod
	def lookup(t) -> list[tuple[UUID, str]]:
		ret = []
		ts = DiskTypesGPT.types
		from builder.disk.layout.gpt.part import DiskPartGPT
		from builder.disk.layout.gpt.struct import EfiPartEntry
		if isinstance(t, DiskPartGPT):
			u = t.type_uuid
		elif isinstance(t, EfiPartEntry):
			u = t.type_guid.to_uuid()
		elif type(t) is EfiGUID:
			u = t.to_uuid()
		elif type(t) is UUID:
			u = t
		elif type(t) is str:
			ret = [tn for tn in ts if tn[1] == t]
			if len(ret) > 0: return ret
			try: u = UUID(t)
			except: return ret
		else: return ret
		return [tn for tn in ts if tn[0] == u]

	def lookup_one(t) -> tuple[UUID, str]:
		l = DiskTypesGPT.lookup(t)
		return l[0] if len(l) > 0 else None

	@staticmethod
	def lookup_one_uuid(t) -> UUID:
		r = DiskTypesGPT.lookup_one(t)
		return r[0] if r else None

	@staticmethod
	def lookup_one_guid(t) -> EfiGUID:
		u = DiskTypesGPT.lookup_one_uuid(t)
		return EfiGUID.from_uuid(u)

	@staticmethod
	def lookup_one_name(t) -> str:
		r = DiskTypesGPT.lookup_one(t)
		return r[1] if r else None

	@staticmethod
	def lookup_names(t) -> list[str]:
		r = DiskTypesGPT.lookup(t)
		return [t[1] for t in r]

	@staticmethod
	def equal(l, r) -> bool:
		lf = DiskTypesGPT.lookup_one_uuid(l)
		rf = DiskTypesGPT.lookup_one_uuid(r)
		if lf is None or rf is None: return False
		return lf == rf

	types: list[tuple[UUID, str]] = [
		(UUID("C12A7328-F81F-11D2-BA4B-00A0C93EC93B"), "efi"),
		(UUID("C12A7328-F81F-11D2-BA4B-00A0C93EC93B"), "uefi"),
		(UUID("C12A7328-F81F-11D2-BA4B-00A0C93EC93B"), "esp"),
		(UUID("024DEE41-33E7-11D3-9D69-0008C781F39F"), "mbr-part-scheme"),
		(UUID("D3BFE2DE-3DAF-11DF-BA40-E3A556D89593"), "intel-fast-flash"),
		(UUID("21686148-6449-6E6F-744E-656564454649"), "bios"),
		(UUID("21686148-6449-6E6F-744E-656564454649"), "bios-boot"),
		(UUID("F4019732-066E-4E12-8273-346C5641494F"), "sony-boot-partition"),
		(UUID("BFBFAFE7-A34F-448A-9A5B-6213EB736C22"), "lenovo-boot-partition"),
		(UUID("9E1A2D38-C612-4316-AA26-8B49521E5A8B"), "powerpc-prep-boot"),
		(UUID("7412F7D5-A156-4B13-81DC-867174929325"), "onie-boot"),
		(UUID("D4E6E2CD-4469-46F3-B5CB-1BFF57AFC149"), "onie-config"),
		(UUID("E3C9E316-0B5C-4DB8-817D-F92DF00215AE"), "microsoft-reserved"),
		(UUID("E3C9E316-0B5C-4DB8-817D-F92DF00215AE"), "msr"),
		(UUID("EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"), "microsoft-basic-data"),
		(UUID("EBD0A0A2-B9E5-4433-87C0-68B6B72699C7"), "basic"),
		(UUID("5808C8AA-7E8F-42E0-85D2-E1E90434CFB3"), "microsoft-ldm-metadata"),
		(UUID("AF9B60A0-1431-4F62-BC68-3311714A69AD"), "microsoft-ldm-data"),
		(UUID("DE94BBA4-06D1-4D40-A16A-BFD50179D6AC"), "windows-recovery-environment"),
		(UUID("E75CAF8F-F680-4CEE-AFA3-B001E56EFC2D"), "microsoft-storage-spaces"),
		(UUID("75894C1E-3AEB-11D3-B7C1-7B03A0000000"), "hp-ux-data"),
		(UUID("E2A1E728-32E3-11D6-A682-7B03A0000000"), "hp-ux-service"),
		(UUID("0657FD6D-A4AB-43C4-84E5-0933C84B4F4F"), "linux-swap"),
		(UUID("0FC63DAF-8483-4772-8E79-3D69D8477DE4"), "linux"),
		(UUID("0FC63DAF-8483-4772-8E79-3D69D8477DE4"), "linux-filesystem"),
		(UUID("3B8F8425-20E0-4F3B-907F-1A25A76F98E8"), "linux-server-data"),
		(UUID("3B8F8425-20E0-4F3B-907F-1A25A76F98E8"), "linux-srv"),
		(UUID("44479540-F297-41B2-9AF7-D131D5F0458A"), "linux-root-x86"),
		(UUID("4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709"), "linux-root-x86-64"),
		(UUID("4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709"), "linux-root-x86_64"),
		(UUID("4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709"), "linux-root-x64"),
		(UUID("6523F8AE-3EB1-4E2A-A05A-18B695AE656F"), "linux-root-alpha"),
		(UUID("D27F46ED-2919-4CB8-BD25-9531F3C16534"), "linux-root-arc"),
		(UUID("69DAD710-2CE4-4E3C-B16C-21A1D49ABED3"), "linux-root-arm"),
		(UUID("69DAD710-2CE4-4E3C-B16C-21A1D49ABED3"), "linux-root-armv7h"),
		(UUID("B921B045-1DF0-41C3-AF44-4C6F280D3FAE"), "linux-root-arm64"),
		(UUID("B921B045-1DF0-41C3-AF44-4C6F280D3FAE"), "linux-root-aarch64"),
		(UUID("993D8D3D-F80E-4225-855A-9DAF8ED7EA97"), "linux-root-ia64"),
		(UUID("77055800-792C-4F94-B39A-98C91B762BB6"), "linux-root-loongarch64"),
		(UUID("37C58C8A-D913-4156-A25F-48B1B64E07F0"), "linux-root-mips32le"),
		(UUID("700BDA43-7A34-4507-B179-EEB93D7A7CA3"), "linux-root-mips64le"),
		(UUID("1AACDB3B-5444-4138-BD9E-E5C2239B2346"), "linux-root-hppa"),
		(UUID("1DE3F1EF-FA98-47B5-8DCD-4A860A654D78"), "linux-root-ppc"),
		(UUID("912ADE1D-A839-4913-8964-A10EEE08FBD2"), "linux-root-ppc64"),
		(UUID("C31C45E6-3F39-412E-80FB-4809C4980599"), "linux-root-ppc64le"),
		(UUID("60D5A7FE-8E7D-435C-B714-3DD8162144E1"), "linux-root-riscv32"),
		(UUID("72EC70A6-CF74-40E6-BD49-4BDA08E8F224"), "linux-root-riscv64"),
		(UUID("08A7ACEA-624C-4A20-91E8-6E0FA67D23F9"), "linux-root-s390"),
		(UUID("5EEAD9A9-FE09-4A1E-A1D7-520D00531306"), "linux-root-s390x"),
		(UUID("C50CDD70-3862-4CC3-90E1-809A8C93EE2C"), "linux-root-tilegx"),
		(UUID("8DA63339-0007-60C0-C436-083AC8230908"), "linux-reserved"),
		(UUID("933AC7E1-2EB4-4F13-B844-0E14E2AEF915"), "linux-home"),
		(UUID("A19D880F-05FC-4D3B-A006-743F0F84911E"), "linux-raid"),
		(UUID("E6D6D379-F507-44C2-A23C-238F2A3DF928"), "linux-lvm"),
		(UUID("4D21B016-B534-45C2-A9FB-5C16E091FD2D"), "linux-variable-data"),
		(UUID("4D21B016-B534-45C2-A9FB-5C16E091FD2D"), "linux-var-data"),
		(UUID("4D21B016-B534-45C2-A9FB-5C16E091FD2D"), "linux-var"),
		(UUID("7EC6F557-3BC5-4ACA-B293-16EF5DF639D1"), "linux-temporary-data"),
		(UUID("7EC6F557-3BC5-4ACA-B293-16EF5DF639D1"), "linux-tmp-data"),
		(UUID("7EC6F557-3BC5-4ACA-B293-16EF5DF639D1"), "linux-tmp"),
		(UUID("75250D76-8CC6-458E-BD66-BD47CC81A812"), "linux-usr-x86"),
		(UUID("8484680C-9521-48C6-9C11-B0720656F69E"), "linux-usr-x86-64"),
		(UUID("8484680C-9521-48C6-9C11-B0720656F69E"), "linux-usr-x86_64"),
		(UUID("8484680C-9521-48C6-9C11-B0720656F69E"), "linux-usr-x64"),
		(UUID("E18CF08C-33EC-4C0D-8246-C6C6FB3DA024"), "linux-usr-alpha"),
		(UUID("7978A683-6316-4922-BBEE-38BFF5A2FECC"), "linux-usr-arc"),
		(UUID("7D0359A3-02B3-4F0A-865C-654403E70625"), "linux-usr-arm"),
		(UUID("B0E01050-EE5F-4390-949A-9101B17104E9"), "linux-usr-arm64"),
		(UUID("B0E01050-EE5F-4390-949A-9101B17104E9"), "linux-usr-aarch64"),
		(UUID("4301D2A6-4E3B-4B2A-BB94-9E0B2C4225EA"), "linux-usr-ia64"),
		(UUID("E611C702-575C-4CBE-9A46-434FA0BF7E3F"), "linux-usr-loongarch64"),
		(UUID("0F4868E9-9952-4706-979F-3ED3A473E947"), "linux-usr-mips32le"),
		(UUID("C97C1F32-BA06-40B4-9F22-236061B08AA8"), "linux-usr-mips64le"),
		(UUID("DC4A4480-6917-4262-A4EC-DB9384949F25"), "linux-usr-hppa"),
		(UUID("7D14FEC5-CC71-415D-9D6C-06BF0B3C3EAF"), "linux-usr-ppc"),
		(UUID("2C9739E2-F068-46B3-9FD0-01C5A9AFBCCA"), "linux-usr-ppc64"),
		(UUID("15BB03AF-77E7-4D4A-B12B-C0D084F7491C"), "linux-usr-ppc64le"),
		(UUID("B933FB22-5C3F-4F91-AF90-E2BB0FA50702"), "linux-usr-riscv32"),
		(UUID("BEAEC34B-8442-439B-A40B-984381ED097D"), "linux-usr-riscv64"),
		(UUID("CD0F869B-D0FB-4CA0-B141-9EA87CC78D66"), "linux-usr-s390"),
		(UUID("8A4F5770-50AA-4ED3-874A-99B710DB6FEA"), "linux-usr-s390x"),
		(UUID("55497029-C7C1-44CC-AA39-815ED1558630"), "linux-usr-tilegx"),
		(UUID("D13C5D3B-B5D1-422A-B29F-9454FDC89D76"), "linux-root-verity-x86"),
		(UUID("2C7357ED-EBD2-46D9-AEC1-23D437EC2BF5"), "linux-root-verity-x86-64"),
		(UUID("2C7357ED-EBD2-46D9-AEC1-23D437EC2BF5"), "linux-root-verity-x86_64"),
		(UUID("2C7357ED-EBD2-46D9-AEC1-23D437EC2BF5"), "linux-root-verity-x64"),
		(UUID("FC56D9E9-E6E5-4C06-BE32-E74407CE09A5"), "linux-root-verity-alpha"),
		(UUID("24B2D975-0F97-4521-AFA1-CD531E421B8D"), "linux-root-verity-arc"),
		(UUID("7386CDF2-203C-47A9-A498-F2ECCE45A2D6"), "linux-root-verity-arm"),
		(UUID("7386CDF2-203C-47A9-A498-F2ECCE45A2D6"), "linux-root-verity-armv7h"),
		(UUID("DF3300CE-D69F-4C92-978C-9BFB0F38D820"), "linux-root-verity-arm64"),
		(UUID("DF3300CE-D69F-4C92-978C-9BFB0F38D820"), "linux-root-verity-aarch64"),
		(UUID("86ED10D5-B607-45BB-8957-D350F23D0571"), "linux-root-verity-ia64"),
		(UUID("F3393B22-E9AF-4613-A948-9D3BFBD0C535"), "linux-root-verity-loongarch64"),
		(UUID("D7D150D2-2A04-4A33-8F12-16651205FF7B"), "linux-root-verity-mips32le"),
		(UUID("16B417F8-3E06-4F57-8DD2-9B5232F41AA6"), "linux-root-verity-mips64le"),
		(UUID("D212A430-FBC5-49F9-A983-A7FEEF2B8D0E"), "linux-root-verity-hppa"),
		(UUID("98CFE649-1588-46DC-B2F0-ADD147424925"), "linux-root-verity-ppc"),
		(UUID("9225A9A3-3C19-4D89-B4F6-EEFF88F17631"), "linux-root-verity-ppc64"),
		(UUID("906BD944-4589-4AAE-A4E4-DD983917446A"), "linux-root-verity-ppc64le"),
		(UUID("AE0253BE-1167-4007-AC68-43926C14C5DE"), "linux-root-verity-riscv32"),
		(UUID("B6ED5582-440B-4209-B8DA-5FF7C419EA3D"), "linux-root-verity-riscv64"),
		(UUID("7AC63B47-B25C-463B-8DF8-B4A94E6C90E1"), "linux-root-verity-s390"),
		(UUID("B325BFBE-C7BE-4AB8-8357-139E652D2F6B"), "linux-root-verity-s390x"),
		(UUID("966061EC-28E4-4B2E-B4A5-1F0A825A1D84"), "linux-root-verity-tilegx"),
		(UUID("8F461B0D-14EE-4E81-9AA9-049B6FB97ABD"), "linux-usr-verity-x86"),
		(UUID("77FF5F63-E7B6-4633-ACF4-1565B864C0E6"), "linux-usr-verity-x86-64"),
		(UUID("77FF5F63-E7B6-4633-ACF4-1565B864C0E6"), "linux-usr-verity-x86_64"),
		(UUID("77FF5F63-E7B6-4633-ACF4-1565B864C0E6"), "linux-usr-verity-x64"),
		(UUID("8CCE0D25-C0D0-4A44-BD87-46331BF1DF67"), "linux-usr-verity-alpha"),
		(UUID("FCA0598C-D880-4591-8C16-4EDA05C7347C"), "linux-usr-verity-arc"),
		(UUID("C215D751-7BCD-4649-BE90-6627490A4C05"), "linux-usr-verity-arm"),
		(UUID("C215D751-7BCD-4649-BE90-6627490A4C05"), "linux-usr-verity-armv7h"),
		(UUID("6E11A4E7-FBCA-4DED-B9E9-E1A512BB664E"), "linux-usr-verity-arm64"),
		(UUID("6E11A4E7-FBCA-4DED-B9E9-E1A512BB664E"), "linux-usr-verity-aarch64"),
		(UUID("6A491E03-3BE7-4545-8E38-83320E0EA880"), "linux-usr-verity-ia64"),
		(UUID("F46B2C26-59AE-48F0-9106-C50ED47F673D"), "linux-usr-verity-loongarch64"),
		(UUID("46B98D8D-B55C-4E8F-AAB3-37FCA7F80752"), "linux-usr-verity-mips32le"),
		(UUID("3C3D61FE-B5F3-414D-BB71-8739A694A4EF"), "linux-usr-verity-mips64le"),
		(UUID("5843D618-EC37-48D7-9F12-CEA8E08768B2"), "linux-usr-verity-hppa"),
		(UUID("DF765D00-270E-49E5-BC75-F47BB2118B09"), "linux-usr-verity-ppc"),
		(UUID("BDB528A5-A259-475F-A87D-DA53FA736A07"), "linux-usr-verity-ppc64"),
		(UUID("EE2B9983-21E8-4153-86D9-B6901A54D1CE"), "linux-usr-verity-ppc64le"),
		(UUID("CB1EE4E3-8CD0-4136-A0A4-AA61A32E8730"), "linux-usr-verity-riscv32"),
		(UUID("8F1056BE-9B05-47C4-81D6-BE53128E5B54"), "linux-usr-verity-riscv64"),
		(UUID("B663C618-E7BC-4D6D-90AA-11B756BB1797"), "linux-usr-verity-s390"),
		(UUID("31741CC4-1A2A-4111-A581-E00B447D2D06"), "linux-usr-verity-s390x"),
		(UUID("2FB4BF56-07FA-42DA-8132-6B139F2026AE"), "linux-usr-verity-tilegx"),
		(UUID("5996FC05-109C-48DE-808B-23FA0830B676"), "linux-root-verity-sign-x86"),
		(UUID("41092B05-9FC8-4523-994F-2DEF0408B176"), "linux-root-verity-sign-x86-64"),
		(UUID("41092B05-9FC8-4523-994F-2DEF0408B176"), "linux-root-verity-sign-x86_64"),
		(UUID("41092B05-9FC8-4523-994F-2DEF0408B176"), "linux-root-verity-sign-x64"),
		(UUID("D46495B7-A053-414F-80F7-700C99921EF8"), "linux-root-verity-sign-alpha"),
		(UUID("143A70BA-CBD3-4F06-919F-6C05683A78BC"), "linux-root-verity-sign-arc"),
		(UUID("42B0455F-EB11-491D-98D3-56145BA9D037"), "linux-root-verity-sign-arm"),
		(UUID("42B0455F-EB11-491D-98D3-56145BA9D037"), "linux-root-verity-sign-armv7h"),
		(UUID("6DB69DE6-29F4-4758-A7A5-962190F00CE3"), "linux-root-verity-sign-arm64"),
		(UUID("6DB69DE6-29F4-4758-A7A5-962190F00CE3"), "linux-root-verity-sign-aarch64"),
		(UUID("E98B36EE-32BA-4882-9B12-0CE14655F46A"), "linux-root-verity-sign-ia64"),
		(UUID("5AFB67EB-ECC8-4F85-AE8E-AC1E7C50E7D0"), "linux-root-verity-sign-loongarch64"),
		(UUID("C919CC1F-4456-4EFF-918C-F75E94525CA5"), "linux-root-verity-sign-mips32le"),
		(UUID("904E58EF-5C65-4A31-9C57-6AF5FC7C5DE7"), "linux-root-verity-sign-mips64le"),
		(UUID("15DE6170-65D3-431C-916E-B0DCD8393F25"), "linux-root-verity-sign-hppa"),
		(UUID("1B31B5AA-ADD9-463A-B2ED-BD467FC857E7"), "linux-root-verity-sign-ppc"),
		(UUID("F5E2C20C-45B2-4FFA-BCE9-2A60737E1AAF"), "linux-root-verity-sign-ppc64"),
		(UUID("D4A236E7-E873-4C07-BF1D-BF6CF7F1C3C6"), "linux-root-verity-sign-ppc64le"),
		(UUID("3A112A75-8729-4380-B4CF-764D79934448"), "linux-root-verity-sign-riscv32"),
		(UUID("EFE0F087-EA8D-4469-821A-4C2A96A8386A"), "linux-root-verity-sign-riscv64"),
		(UUID("3482388E-4254-435A-A241-766A065F9960"), "linux-root-verity-sign-s390"),
		(UUID("C80187A5-73A3-491A-901A-017C3FA953E9"), "linux-root-verity-sign-s390x"),
		(UUID("B3671439-97B0-4A53-90F7-2D5A8F3AD47B"), "linux-root-verity-sign-tilegx"),
		(UUID("974A71C0-DE41-43C3-BE5D-5C5CCD1AD2C0"), "linux-usr-verity-sign-x86"),
		(UUID("E7BB33FB-06CF-4E81-8273-E543B413E2E2"), "linux-usr-verity-sign-x86-64"),
		(UUID("E7BB33FB-06CF-4E81-8273-E543B413E2E2"), "linux-usr-verity-sign-x86_64"),
		(UUID("E7BB33FB-06CF-4E81-8273-E543B413E2E2"), "linux-usr-verity-sign-x64"),
		(UUID("5C6E1C76-076A-457A-A0FE-F3B4CD21CE6E"), "linux-usr-verity-sign-alpha"),
		(UUID("94F9A9A1-9971-427A-A400-50CB297F0F35"), "linux-usr-verity-sign-arc"),
		(UUID("D7FF812F-37D1-4902-A810-D76BA57B975A"), "linux-usr-verity-sign-arm"),
		(UUID("D7FF812F-37D1-4902-A810-D76BA57B975A"), "linux-usr-verity-sign-armv7h"),
		(UUID("C23CE4FF-44BD-4B00-B2D4-B41B3419E02A"), "linux-usr-verity-sign-arm64"),
		(UUID("C23CE4FF-44BD-4B00-B2D4-B41B3419E02A"), "linux-usr-verity-sign-aarch64"),
		(UUID("8DE58BC2-2A43-460D-B14E-A76E4A17B47F"), "linux-usr-verity-sign-ia64"),
		(UUID("B024F315-D330-444C-8461-44BBDE524E99"), "linux-usr-verity-sign-loongarch64"),
		(UUID("3E23CA0B-A4BC-4B4E-8087-5AB6A26AA8A9"), "linux-usr-verity-sign-mips32le"),
		(UUID("F2C2C7EE-ADCC-4351-B5C6-EE9816B66E16"), "linux-usr-verity-sign-mips64le"),
		(UUID("450DD7D1-3224-45EC-9CF2-A43A346D71EE"), "linux-usr-verity-sign-hppa"),
		(UUID("7007891D-D371-4A80-86A4-5CB875B9302E"), "linux-usr-verity-sign-ppc"),
		(UUID("0B888863-D7F8-4D9E-9766-239FCE4D58AF"), "linux-usr-verity-sign-ppc64"),
		(UUID("C8BFBD1E-268E-4521-8BBA-BF314C399557"), "linux-usr-verity-sign-ppc64le"),
		(UUID("C3836A13-3137-45BA-B583-B16C50FE5EB4"), "linux-usr-verity-sign-riscv32"),
		(UUID("D2F9000A-7A18-453F-B5CD-4D32F77A7B32"), "linux-usr-verity-sign-riscv64"),
		(UUID("17440E4F-A8D0-467F-A46E-3912AE6EF2C5"), "linux-usr-verity-sign-s390"),
		(UUID("3F324816-667B-46AE-86EE-9B0C0C6C11B4"), "linux-usr-verity-sign-s390x"),
		(UUID("4EDE75E2-6CCC-4CC8-B9C7-70334B087510"), "linux-usr-verity-sign-tilegx"),
		(UUID("BC13C2FF-59E6-4262-A352-B275FD6F7172"), "linux-extended-boot"),
		(UUID("773f91ef-66d4-49b5-bd83-d683bf40ad16"), "linux-home"),
		(UUID("516E7CB4-6ECF-11D6-8FF8-00022D09712B"), "freebsd-data"),
		(UUID("83BD6B9D-7F41-11DC-BE0B-001560B84F0F"), "freebsd-boot"),
		(UUID("516E7CB5-6ECF-11D6-8FF8-00022D09712B"), "freebsd-swap"),
		(UUID("516E7CB6-6ECF-11D6-8FF8-00022D09712B"), "freebsd-ufs"),
		(UUID("516E7CBA-6ECF-11D6-8FF8-00022D09712B"), "freebsd-zfs"),
		(UUID("516E7CB8-6ECF-11D6-8FF8-00022D09712B"), "freebsd-vinum"),
		(UUID("48465300-0000-11AA-AA11-00306543ECAC"), "apple-hfs"),
		(UUID("7C3457EF-0000-11AA-AA11-00306543ECAC"), "apple-apfs"),
		(UUID("55465300-0000-11AA-AA11-00306543ECAC"), "apple-ufs"),
		(UUID("52414944-0000-11AA-AA11-00306543ECAC"), "apple-raid"),
		(UUID("52414944-5F4F-11AA-AA11-00306543ECAC"), "apple-raid-offline"),
		(UUID("426F6F74-0000-11AA-AA11-00306543ECAC"), "apple-boot"),
		(UUID("4C616265-6C00-11AA-AA11-00306543ECAC"), "apple-label"),
		(UUID("5265636F-7665-11AA-AA11-00306543ECAC"), "apple-tv-recovery"),
		(UUID("53746F72-6167-11AA-AA11-00306543ECAC"), "apple-core-storage"),
		(UUID("69646961-6700-11AA-AA11-00306543ECAC"), "apple-silicon-boot"),
		(UUID("52637672-7900-11AA-AA11-00306543ECAC"), "apple-silicon-recovery"),
		(UUID("6A82CB45-1DD2-11B2-99A6-080020736631"), "solaris-boot"),
		(UUID("6A85CF4D-1DD2-11B2-99A6-080020736631"), "solaris-root"),
		(UUID("6A898CC3-1DD2-11B2-99A6-080020736631"), "solaris-usr"),
		(UUID("6A87C46F-1DD2-11B2-99A6-080020736631"), "solaris-swap"),
		(UUID("6A8B642B-1DD2-11B2-99A6-080020736631"), "solaris-backup"),
		(UUID("6A8EF2E9-1DD2-11B2-99A6-080020736631"), "solaris-var"),
		(UUID("6A90BA39-1DD2-11B2-99A6-080020736631"), "solaris-home"),
		(UUID("49F48D32-B10E-11DC-B99B-0019D1879648"), "netbsd-swap"),
		(UUID("49F48D5A-B10E-11DC-B99B-0019D1879648"), "netbsd-ffs"),
		(UUID("49F48D82-B10E-11DC-B99B-0019D1879648"), "netbsd-lfs"),
		(UUID("2DB519C4-B10F-11DC-B99B-0019D1879648"), "netbsd-concatenated"),
		(UUID("2DB519EC-B10F-11DC-B99B-0019D1879648"), "netbsd-encrypted"),
		(UUID("49F48DAA-B10E-11DC-B99B-0019D1879648"), "netbsd-raid"),
		(UUID("FE3A2A5D-4F32-41A7-B725-ACCC3285A309"), "chromeos-kernel"),
		(UUID("3CB8E202-3B7E-47DD-8A3C-7FF2A13CFCEC"), "chromeos-rootfs"),
		(UUID("2E0A753D-9E48-43B0-8337-B15192CB1B5E"), "chromeos-reserved"),
		(UUID("CAB6E88E-ABF3-4102-A07A-D4BB9BE3C1D3"), "chromeos-firmware"),
		(UUID("09845860-705F-4BB5-B16C-8A8A099CAF52"), "chromeos-minios"),
		(UUID("3F0F8318-F146-4E6B-8222-C28C8F02E0D5"), "chromeos-hibernate"),
		(UUID("45B0969E-9B03-4F30-B4C6-B4B80CEFF106"), "ceph-journal"),
		(UUID("45B0969E-9B03-4F30-B4C6-5EC00CEFF106"), "ceph-encrypted-journal"),
		(UUID("4FBD7E29-9D25-41B8-AFD0-062C0CEFF05D"), "ceph-osd"),
		(UUID("4FBD7E29-9D25-41B8-AFD0-5EC00CEFF05D"), "ceph-crypt-osd"),
		(UUID("AA31E02A-400F-11DB-9590-000C2911D1B8"), "vmware-vmfs"),
		(UUID("9D275380-40AD-11DB-BF97-000C2911D1B8"), "vmware-diagnostic"),
		(UUID("381CFCCC-7288-11E0-92EE-000C2911D0B2"), "vmware-vsan"),
		(UUID("77719A0C-A4A0-11E3-A47E-000C29745A24"), "vmware-virsto"),
		(UUID("9198EFFC-31C0-11DB-8F78-000C2911D1B8"), "vmware-reserved"),
		(UUID("824CC7A0-36A8-11E3-890A-952519AD3F61"), "openbsd-data"),
		(UUID("3DE21764-95BD-54BD-A5C3-4ABE786F38A8"), "uboot-env"),
	]
