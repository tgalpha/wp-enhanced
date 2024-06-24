#pragma once
// [wp-enhanced template] **Do not delete this line**

#include "../%(name)sPlugin.h"
//  [wp-enhanced] Uncomment the following lines if you want to use a custom GUI
//  #include "../resource.h"

class %(name)sPluginGUI final
	: public AK::Wwise::Plugin::PluginMFCWindows<>
	, public AK::Wwise::Plugin::GUIWindows
{
public:
	%(name)sPluginGUI();

//  [wp-enhanced] Uncomment the following lines if you want to use a custom GUI
// 	HINSTANCE GetResourceHandle() const override;
//
// 	bool GetDialog(
// 		AK::Wwise::Plugin::eDialog in_eDialog,
// 		UINT& out_uiDialogID,
// 		AK::Wwise::Plugin::PopulateTableItem*& out_pTable
// 	) const override;
//
// 	bool WindowProc(
// 		AK::Wwise::Plugin::eDialog in_eDialog,
// 		HWND in_hWnd,
// 		uint32_t in_message,
// 		WPARAM in_wParam,
// 		LPARAM in_lParam,
// 		LRESULT& out_lResult
// 	) override;
//
// private:
// 	HWND m_hwndPropView = nullptr;
};
